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


# example custom request handler
class IndexHandler(RequestHandler):
    @coroutine
    def get(self):
        self.render("index.html", version="0.0.1dev")


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
    template_dir = os.path.dirname(os.path.abspath(servreg.templates.__file__))

    # setup your static files
    static_dirs = [
        (r"/static", os.path.dirname(os.path.abspath(servreg.static.__file__))),
    ]

    def __init__(self, host, port, dburl):
        self.host = host
        self.port = port

        self.db_engine = init_database(dburl)
        Session.configure(bind=self.db_engine)
        Base.metadata.create_all(self.db_engine)

        super(ServiceRegistry, self).__init__()

    @public_method
    def register_service(self, name, host, port):

        session = Session()
        existent_service = session.query(Service).filter(Service.host == host, Service.port == port).all()
        if not existent_service:
            service = Service(name=name, host=host, port=port)
        else:
            service = existent_service[0]
            service.last_seen = datetime.datetime.now()

        session.add(service)
        session.commit()

        return True

    @private_api_method
    def say_private_hello(self, name):
        """
        Retrieves a value that was previously stored.
        """
        return "Private hello {0}".format(name)

    # Implement your token validation logic
    def api_token_is_valid(self, api_token):
        return True


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
