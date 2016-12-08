import os
import datetime

from tornado.web import RequestHandler
from tornado.gen import coroutine
import click

from pymicroservice.core.microservice import PyMicroService
from pymicroservice.core.decorators import public_method, private_api_method

import servreg.static
import servreg.templates
from servreg.database import init_database, Service, Base, Session

STATIC_DIR = os.path.dirname(os.path.abspath(servreg.static.__file__))
TEMPLATES_DIR = os.path.dirname(os.path.abspath(servreg.templates.__file__))
print(STATIC_DIR)
print(TEMPLATES_DIR)


# example custom request handler
class IndexHandler(RequestHandler):
    @coroutine
    def get(self):
        session = Session()
        self.render("index.html", version="0.0.1dev", services=session.query(Service).filter())


class ServiceRegistry(PyMicroService):
    name = "service.registry"
    host = "127.0.0.1"
    port = 5000

    api_token_header = "X-Api-Token"
    max_parallel_blocking_tasks = os.cpu_count()

    extra_handlers = [
        (r"/", IndexHandler),
    ]

    # create your templates
    template_dir = TEMPLATES_DIR

    # setup your static files
    static_dirs = [
        (r"/static", STATIC_DIR),
    ]

    def __init__(self, host, port, dburl):
        self.host = host
        self.port = port

        self.db_engine = init_database(dburl)
        Session.configure(bind=self.db_engine)
        Base.metadata.create_all(self.db_engine)

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


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8000)
@click.option("--dburl", default="sqlite:///servreg.sqlite3")
def main(host, port, dburl):
    print(host, port, dburl)
    service = ServiceRegistry(host, port, dburl)
    service.start()


if __name__ == '__main__':
    main()
