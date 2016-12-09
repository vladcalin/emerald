import datetime
import humanize
import psutil
import re

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Sequence, Index, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Session = sessionmaker()


def init_database(dburl):
    engine = create_engine(dburl)
    print("created engine {}".format(engine))
    return engine


def get_session_class():
    return sessionmaker()


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


class PerformanceParameters(Base):
    __tablename__ = "servreg_perf"

    id = Column(Integer, Sequence("seq_id_perf"), primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)

    cpu_usage = Column(Float)
    memory_usage_current = Column(Float)
    memory_usage_total = Column(Float)
    avg_response_time = Column(Float)
    request_count = Column(Integer)

    @classmethod
    def save_current_params(cls, session, access_log_path):
        instance = cls()
        instance.cpu_usage = psutil.cpu_percent()

        memory = psutil.virtual_memory()
        instance.memory_usage_current, instance.memory_usage_total = memory.used, memory.total

        with open(access_log_path) as f:
            content = f.read()

        # "2016-12-09 12:16.*?/api.*?[\d.]+ms
        last_minute = datetime.datetime.now() - datetime.timedelta(seconds=60)
        regex = last_minute.strftime("%Y-%m-%d %H:%M") + ".*?/api.*?([\d.]+)ms"
        data = re.findall(regex, content)

        if data:
            instance.avg_response_time = sum([float(x) for x in data]) / len(data)
        else:
            instance.avg_response_time = 0

        instance.request_count = len(data)

        session.add(instance)
        session.commit()

    @classmethod
    def get_items_from_last_hours(cls, session, hours):
        yesterday = datetime.datetime.now() - datetime.timedelta(hours=hours)
        return [x for x in
                session.query(cls).filter(cls.timestamp >= yesterday)]

    def human_readable_memory_current(self):
        return humanize.naturalsize(self.memory_usage_current, format="%.2f")

    def human_readable_memory_total(self):
        return humanize.naturalsize(self.memory_usage_total, format="%.2f")

    def memory_usage_percent(self):
        return self.memory_usage_current / self.memory_usage_total * 100

    def sanitized_timestamp(self):
        # 2012-02-24 15:00:00 for Morris.js
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
