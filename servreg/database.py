import datetime

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Sequence
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
    last_seen = Column(DateTime)

