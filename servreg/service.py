import os
import datetime
import time
import threading
import logging
import logging.handlers

from tornado.web import RequestHandler
from tornado.gen import coroutine
import click
import psutil
import humanize

from pymicroservice.core.microservice import PyMicroService
from pymicroservice.core.decorators import public_method, private_api_method

import servreg.static
import servreg.templates
from servreg.database import init_database, Service, Base, Session, PerformanceParameters
from . import __version__

STATIC_DIR = os.path.dirname(os.path.abspath(servreg.static.__file__))
TEMPLATES_DIR = os.path.dirname(os.path.abspath(servreg.templates.__file__))
print(STATIC_DIR)
print(TEMPLATES_DIR)


# example custom request handler
class ServicesHandler(RequestHandler):
    @coroutine
    def get(self):
        session = Session()
        items = [s for s in session.query(Service).filter()]
        session.close()
        self.render("index.html", version=__version__, services=list(sorted(items, key=lambda x: x.is_alive())))


class StatusHandler(RequestHandler):
    @coroutine
    def get(self):
        session = Session()

        hours = self.get_argument("hours", 24)
        items = PerformanceParameters.get_items_from_last_hours(session, hours=int(hours))
        service_count = session.query(Service).count()

        req_count_today = sum([x.request_count for x in items])
        perf_count = session.query(PerformanceParameters).count()

        relevant_items = [x.avg_response_time for x in items if x.avg_response_time != 0]
        if relevant_items:
            avg_response_time = sum(relevant_items) / len(relevant_items)
        else:
            avg_response_time = 0

        session.close()
        memory_stats = psutil.virtual_memory()
        self.render("status.html", version=__version__,
                    max_memory=humanize.naturalsize(memory_stats.total),
                    memory_used=humanize.naturalsize(memory_stats.used),
                    avg_response_time=avg_response_time,
                    service_count=service_count, req_count_today=req_count_today, perf_count=perf_count,
                    cpu_current=psutil.cpu_percent(), memory_percent=(memory_stats.used / memory_stats.total) * 100)


class HomeHandler(RequestHandler):
    @coroutine
    def get(self):
        self.render("home.html", version=__version__)


class IndexHandler(RequestHandler):
    @coroutine
    def get(self):
        self.redirect("/home", permanent=True)


class ServiceRegistry(PyMicroService):
    name = "service.registry"
    host = "127.0.0.1"
    port = 5000

    api_token_header = "X-Api-Token"
    max_parallel_blocking_tasks = os.cpu_count()

    extra_handlers = [
        (r"/", IndexHandler),
        (r"/services", ServicesHandler),
        (r"/status", StatusHandler),
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

        super(ServiceRegistry, self).__init__()

    @public_method
    def ping(self, name, host, port):
        """Acknowledges the existence of a service. If the service was previously registered (exists in db),
        its stats will be updated (last ping time and name if does not match)"""
        session = Session()
        existent_service = session.query(Service).filter(Service.host == host, Service.port == port).all()
        if not existent_service:
            service = Service(name=name, host=host, port=port)
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
        return [{"host": service.host, "port": service.port}
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


class PerformanceMonitorThread(threading.Thread):
    def __init__(self, dburl, access_log):
        self.db_engine = init_database(dburl)
        self.access_log = access_log
        super(PerformanceMonitorThread, self).__init__()

    def run(self):
        while True:
            session = Session(bind=self.db_engine)
            PerformanceParameters.save_current_params(session=session, access_log_path=self.access_log)
            session.close()
            time.sleep(60)


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8000)
@click.option("--dburl", default="sqlite:///servreg.sqlite3")
@click.option("--accesslog", default="access.log")
def main(host, port, dburl, accesslog):
    print(host, port, dburl)
    engine = init_database(dburl)
    Session.configure(bind=engine)

    Base.metadata.create_all(engine)

    perfmon = PerformanceMonitorThread(dburl, accesslog)
    perfmon.start()

    service = ServiceRegistry(host, port, dburl, accesslog)
    service.start()


if __name__ == '__main__':
    main()
