import os
import datetime
import time
import threading
import logging
import logging.handlers
import functools

from tornado.web import RequestHandler
from tornado.gen import coroutine
import click
import psutil
import humanize

from gemstone import MicroService, public_method, private_api_method

import emerald.static
import emerald.templates
from emerald.database import init_database, Service, Base, Session, Incident
from emerald.tasks import update_services_status
from . import __version__

STATIC_DIR = os.path.dirname(os.path.abspath(emerald.static.__file__))
TEMPLATES_DIR = os.path.dirname(os.path.abspath(emerald.templates.__file__))


class ServicesHandler(RequestHandler):
    @coroutine
    def get(self):
        session = Session()
        items = [s for s in session.query(Service).filter()]
        session.close()
        self.render("services.html", version=__version__, services=list(sorted(items, key=lambda x: x.last_seen)))


class IncidentsHandler(RequestHandler):
    @coroutine
    def get(self):
        session = Session()

        service_count = session.query(Service).count()
        incidents = session.query(Incident).filter()

        session.close()
        memory_stats = psutil.virtual_memory()
        self.render("incidents.html", version=__version__,
                    max_memory=humanize.naturalsize(memory_stats.total),
                    memory_used=humanize.naturalsize(memory_stats.used),
                    service_count=service_count, cpu_current=psutil.cpu_percent(),
                    memory_percent=(memory_stats.used / memory_stats.total) * 100, incidents=incidents)


class HomeHandler(RequestHandler):
    @coroutine
    def get(self):
        self.render("home.html", version=__version__)


class IndexHandler(RequestHandler):
    @coroutine
    def get(self):
        self.redirect("/home", permanent=True)


class EmeraldServiceRegistry(MicroService):
    name = "emerald"
    host = "127.0.0.1"
    port = 5000

    max_parallel_blocking_tasks = os.cpu_count()
    periodic_tasks = [
        (functools.partial(update_services_status, Session), 15)
    ]

    extra_handlers = [
        (r"/", IndexHandler),
        (r"/services", ServicesHandler),
        (r"/status", IncidentsHandler),
        (r"/home", HomeHandler),
    ]

    # create your templates
    template_dir = TEMPLATES_DIR

    # setup your static files
    static_dirs = [
        (r"/static", STATIC_DIR),
    ]

    def __init__(self, host, port, dburl, accesslog):
        self.host = host
        self.port = port
        self.db_engine = init_database(dburl)

        self.init_access_log(accesslog)

        super(EmeraldServiceRegistry, self).__init__()

    @public_method
    def ping(self, name, url):
        """Acknowledges the existence of a service. If the service was previously registered (exists in db),
        its stats will be updated (last ping time and name if does not match)"""
        session = Session()
        existent_service = session.query(Service).filter(Service.url == url).all()
        if not existent_service:
            service = Service(name=name, url=url)
        else:
            service = existent_service[0]
            service.last_seen = datetime.datetime.now()
            service.name = name

        session.add(service)
        session.commit()

        return True

    @public_method
    def locate_service(self, name):
        """Locates all existing services by a given glob expression"""
        name = self.glob_to_sql(name)
        session = Session()
        return [service.url
                for service in session.query(Service).filter(Service.name.like(name)) if service.is_alive()]

    def glob_to_sql(self, name):
        if "*" in name:
            name = name.replace("*", "%")
        if "?" in name:
            name = name.replace("?", "_")
        return name

    def init_access_log(self, accesslog):
        logger = logging.getLogger("tornado.access")

        file_handler = logging.handlers.TimedRotatingFileHandler(accesslog, when="midnight")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        logger.addHandler(file_handler)


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8000)
@click.option("--dburl", default="sqlite:///emerald.sqlite3")
@click.option("--accesslog", default="access.log")
def main(host, port, dburl, accesslog):
    engine = init_database(dburl)
    Session.configure(bind=engine)

    Base.metadata.create_all(engine)

    service = EmeraldServiceRegistry(host, port, dburl, accesslog)
    service.start()


if __name__ == '__main__':
    main()
