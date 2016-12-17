Service registry
================

This is a simple service registry compatible with [pymicroservice](http://github.com/vladcalin/pymicroservice) based 
services which uses JSON RPC protocol for communication and sqlalchemy for data persistance.

What is this?
-------------

This service registry tracks microservices and helps them to identify
each other with little knowledge (just the location of the service registry.

This service is implemented using te [pymicroservice](http://github.com/vladcalin/pymicroservice)
library and exposes the following methods:

- ``ping(name, host, port)`` - registers the fact that at ``http://host:port/api``
  is a service running with the name ``name``. A service must call ping at least
  once every 60 seconds in order to be considered active.
- ``locate_service(name)`` - locates a service based on a given pattern (glob-like pattern).
  returns a list of ``{host: ..., port: ...}` (multiple instances of the same service
  can run at the same time).
  
Installation
------------

```
    pip install servreg
```

or 

```
    git clone https://github.com/vladcalin/servreg.git
    python servreg/setup.py install
```

To run the tests, use the command

```
    python servreg/setup.py test
```

Start the service
-----------------

In order to start the service at ``http://0.0.0.0:5000/api``, use the command

```
    servreg --host=0.0.0.0 --port=0.0.0.0 --dburl=sqlite:///:memory: --accesslog=access.log
```

The following parameters can be specified:

- ``--host`` = the address to bind
- ``--port`` = the port to bind
- ``--dburl`` = a database url (as in the 
  [sqlalchemy](http://docs.sqlalchemy.org/en/latest/dialects/index.html) 
  specifications). Here are some quick examples:
    - using SQLite: ``sqlite:///mydatabase.db``, 
      ``sqlite:////etc/run/servreg/servreg.db``, ``sqlite://:memory:``
    - using MySQL: ``mysql+mysqldb://<user>:<password>@<host>:<port>/<dbname>`` (requires mysql-python),
      ``mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>`` (requires pymysql)
    - using Oracle with cx_oracle: ``oracle+cx_oracle://user:pass@host:port/dbname``
    - using PostgreSQL with psycopg2: ``postgresql+psycopg2://user:password@host:port/dbname``
    - using PostgreSQL with pg8000: ``postgresql+pg8000://user:password@host:port/dbname``
    
  **Note** : you must install the database driver separately (except for sqlite).
  
- ``--accesslog`` = the file where the access log will be stored

