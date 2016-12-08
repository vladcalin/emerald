import datetime
import humanize

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Sequence, Index
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Session = sessionmaker()


def init_database(dburl):
    engine = create_engine(dburl)
    print("created engine {}".format(engine))
    return engine


class Service(Base):
    __tablename__ = "servreg_services"

    id = Column(Integer, Sequence("seq_id_service"), primary_key=True)
    name = Column(String)

    host = Column(String)
    port = Column(Integer)

    first_seen = Column(DateTime, default=datetime.datetime.now)
    last_seen = Column(DateTime, default=datetime.datetime.now)

    __table_args__ = (Index("host_port_index", "host", "port", unique=True),)

    def is_alive(self):
        return (datetime.datetime.now() - self.last_seen).total_seconds() <= 60 * 3

    def human_readable_first_seen(self):
        return humanize.naturalday(self.first_seen)

    def human_readable_last_seen(self):
        return humanize.naturaltime(self.last_seen)
