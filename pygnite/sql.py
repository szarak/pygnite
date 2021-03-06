#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of web2py Web Framework (Copyrighted, 2007)
# Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
# License: GPL v2

__all__ = ['database']

import re
import sys
import os
import types
import cPickle
import datetime
import thread
import cStringIO
import csv
import copy
import socket
import logging
import copy_reg
import base64
import hashlib

from utils import hash

table_field = re.compile('[\w_]+\.[\w_]+')
oracle_fix = re.compile("[^']*('[^']*'[^']*)*\:(?P<clob>CLOB\('([^']+|'')*'\))")

drivers = []

try:
    import sqlite3
    drivers.append('SQLite3')
except:
    try:
        from pysqlite2 import dbapi2 as sqlite3
        logging.warning('importing mysqlite3.dbapi2 as sqlite3')
        drivers.append('SQLite2')
    except:
        logging.debug('no sqlite3 or dbapi2 driver')
try:
    import MySQLdb
    drivers.append('MySQL')
except:
    logging.debug('no MySQLdb driver')
try:
    import psycopg2
    drivers.append('Postgre')
except:
    logging.debug('no psycopg2 driver')
try:
    import cx_Oracle
    drivers.append('Oracle')
except:
    logging.debug('no cx_Oracle driver')
try:
    import pyodbc
    drivers.append('MSSQL/DB2')
except:
    logging.debug('no MSSQL/DB2 driver')
try:
    import kinterbasdb
    drivers.append('Interbase')
except:
    logging.debug('no kinterbasdb driver')
try:
    import informixdb
    drivers.append('Informix')
    logging.warning('Informix support is experimental')
except:
    logging.debug('no informixdb driver')
try:
    from com.ziclix.python.sql import zxJDBC
    drivers.append('zxJDBC')
    logging.warning('zxJDBC support is experimental')
except:
    logging.debug('no zxJDBC driver')

import validators

sql_locker = thread.allocate_lock()

def database(engine='sqlite3', db='database.db', host=None, username=None, password=None, port=None):
    """This function is wrapper which returns ``SQLDB`` known from web2py.

    :param engine: Database engine, e.g. ``sqlite3`` or ``mysql``. 
    :param db: If engine is sqlite, path to database, else database name. 
    :param host: Host. Default: `localhost`. 
    :param username: Usename.
    :param password: Password.
    :param port: Port.
    """
    if engine == 'sqlite3':
        if not db.startswith('/'):
            root = sys.path[0]
            db_path = os.path.join(root, db)
            db_folder = os.path.dirname(db_path)

            if not os.path.isdir(db_folder):
                os.makedirs(db_folder)
        else:
            db_path = db

        return SQLDB('sqlite://%s' % db_path)
    elif engine == 'oracle':
        return SQLDB('oracle://%s/%s@%s' % (username, password, db))
    else:
        if port is not None:
            return SQLDB('%s://%s:%s@%s:%s/%s' % (engine, username, password, host or 'localhost', port, db))
        else:
            return SQLDB('%s://%s:%s@%s/%s' % (engine, username, password, host or 'localhost', db))

SQL_DIALECTS = {
    'sqlite': {
        'boolean': 'CHAR(1)',
        'string': 'CHAR(%(length)s)',
        'text': 'TEXT',
        'password': 'CHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'CHAR(128)',
        'integer': 'INTEGER',
        'double': 'DOUBLE',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'reference': 'REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': "web2py_extract('%(name)s',%(field)s)",
        'left join': 'LEFT JOIN',
        'random': 'Random()',
        'notnull': 'NOT NULL DEFAULT %(default)s',
        'substring': 'SUBSTR(%(field)s,%(pos)s,%(length)s)',
        },
    'mysql': {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'LONGTEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'LONGBLOB',
        'upload': 'VARCHAR(128)',
        'integer': 'INT',
        'double': 'DOUBLE',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'DATETIME',
        'id': 'INT AUTO_INCREMENT NOT NULL',
        'reference': 'INT, INDEX %(field_name)s__idx (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'EXTRACT(%(name)s FROM %(field)s)',
        'left join': 'LEFT JOIN',
        'random': 'RAND()',
        'notnull': 'NOT NULL DEFAULT %(default)s',
        'substring': 'SUBSTRING(%(field)s,%(pos)s,%(length)s)',
        },
    'postgres': {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(128)',
        'integer': 'INTEGER',
        'double': 'FLOAT8',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'SERIAL PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'EXTRACT(%(name)s FROM %(field)s)',
        'left join': 'LEFT JOIN',
        'random': 'RANDOM()',
        'notnull': 'NOT NULL DEFAULT %(default)s',
        'substring': 'SUBSTR(%(field)s,%(pos)s,%(length)s)',
        },
    'oracle': {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR2(%(length)s)',
        'text': 'CLOB',
        'password': 'VARCHAR2(%(length)s)',
        'blob': 'CLOB',
        'upload': 'VARCHAR2(128)',
        'integer': 'INT',
        'double': 'FLOAT',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATE',
        'id': 'NUMBER PRIMARY KEY',
        'reference': 'NUMBER, CONSTRAINT %(table_name)s_%(field_name)s__constraint FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'EXTRACT(%(name)s FROM %(field)s)',
        'left join': 'LEFT OUTER JOIN',
        'random': 'dbms_random.value',
        'notnull': 'DEFAULT %(default)s NOT NULL',
        'substring': 'SUBSTR(%(field)s,%(pos)s,%(length)s)',
        },
    'mssql': {
        'boolean': 'BIT',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'VARCHAR(128)',
        'integer': 'INT',
        'double': 'FLOAT',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT, CONSTRAINT %(table_name)s_%(field_name)s__constraint FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'DATEPART(%(name)s,%(field)s)',
        'left join': 'LEFT OUTER JOIN',
        'random': 'NEWID()',
        'notnull': 'NOT NULL DEFAULT %(default)s',
        'substring': 'SUBSTRING(%(field)s,%(pos)s,%(length)s)',
        },
    'mssql2': {
        'boolean': 'CHAR(1)',
        'string': 'NVARCHAR(%(length)s)',
        'text': 'NTEXT',
        'password': 'NVARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'NVARCHAR(128)',
        'integer': 'INT',
        'double': 'FLOAT',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT, CONSTRAINT %(table_name)s_%(field_name)s__constraint FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'DATEPART(%(name)s,%(field)s)',
        'left join': 'LEFT OUTER JOIN',
        'random': 'NEWID()',
        'notnull': 'NOT NULL DEFAULT %(default)s',
        'substring': 'SUBSTRING(%(field)s,%(pos)s,%(length)s)',
        },
    'firebird': {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(128)',
        'integer': 'INTEGER',
        'double': 'FLOAT',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'EXTRACT(%(name)s FROM %(field)s)',
        'left join': 'LEFT JOIN',
        'random': 'RANDOM()',
        'notnull': 'DEFAULT %(default)s NOT NULL',
        'substring': 'SUBSTRING(%(field)s,%(pos)s,%(length)s)',
        },
    'informix': {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(128)',
        'integer': 'INTEGER',
        'double': 'FLOAT',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'SERIAL',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'EXTRACT(%(field)s(%(name)s)',
        'left join': 'LEFT JOIN',
        'random': 'RANDOM()',
        'notnull': 'DEFAULT %(default)s NOT NULL',
        'substring': 'SUBSTR(%(field)s,%(pos)s,%(length)s)',
        },
    'db2': {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'VARCHAR(128)',
        'integer': 'INT',
        'double': 'DOUBLE',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY NOT NULL',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'lower': 'LOWER(%(field)s)',
        'upper': 'UPPER(%(field)s)',
        'is null': 'IS NULL',
        'is not null': 'IS NOT NULL',
        'extract': 'EXTRACT(%(name)s FROM %(field)s)',
        'left join': 'LEFT OUTER JOIN',
        'random': 'RAND()',
        'notnull': 'NOT NULL DEFAULT %(default)s',
        'substring': 'SUBSTR(%(field)s,%(pos)s,%(length)s)',
        },
    }


def sqlhtml_validators(field_type, length):
    v = {
        'boolean': [],
        'string': validators.IS_LENGTH(length),
        'text': validators.IS_LENGTH(2 ** 16),
        'password': validators.IS_LENGTH(length),
        'blob': [],
        'upload': [],
        'double': validators.IS_FLOAT_IN_RANGE(-1e100, 1e100),
        'integer': validators.IS_INT_IN_RANGE(-1e100, 1e100),
        'date': validators.IS_DATE(),
        'time': validators.IS_TIME(),
        'datetime': validators.IS_DATETIME(),
        'reference': validators.IS_INT_IN_RANGE(0, 1e100),
        }
    try:
        return v[field_type[:9]]
    except (KeyError, AttributeError):
        return []


def sql_represent(obj, fieldtype, dbname):
    if isinstance(obj, (SQLXorable, SQLField)):
        return obj
    if obj is None:
        return 'NULL'
    if obj == '' and fieldtype[:2] in ['id', 'in', 're', 'da', 'ti', 'bo']:
        return 'NULL'
    if fieldtype == 'boolean':
        if dbname == 'mssql':
            if obj and not str(obj)[0].upper() == 'F':
                return '1'
            else:
                return '0'
        else:
            if obj and not str(obj)[0].upper() == 'F':
                return "'T'"
            else:
                return "'F'"
    if fieldtype[0] == 'i':
        return str(int(obj))
    elif fieldtype[0] == 'r':
        return str(int(obj))
    elif fieldtype == 'double':
        return str(float(obj))
    if isinstance(obj, unicode):
        obj = obj.encode('utf-8')
    if fieldtype == 'blob':
        obj = base64.b64encode(str(obj))
        if dbname == 'db2':
            return "BLOB('%s')" % obj
        if dbname == 'oracle':
            return ":CLOB('%s')" % obj
    #elif fieldtype == 'text':
    #    if dbname == 'oracle':
    #        return ":CLOB('%s')" % obj.replace("'","?") ### FIX THIS
    elif fieldtype == 'date':

        # if dbname=='postgres': return "'%s'::bytea" % obj.replace("'","''")

        if isinstance(obj, (datetime.date, datetime.datetime)):
            obj = obj.strftime('%Y-%m-%d')
        else:
            obj = str(obj)
        if dbname in ['oracle', 'informix']:
            return "to_date('%s','yyyy-mm-dd')" % obj
    elif fieldtype == 'datetime':
        if isinstance(obj, datetime.datetime):
            if dbname == 'db2':
                return "'%s'" % obj.strftime('%Y-%m-%d-%H.%M.%S')
            else:
                obj = obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            if dbname == 'db2':
                return "'%s'" % obj.strftime('%Y-%m-%d-00.00.00')
            else:
                obj = obj.strftime('%Y-%m-%d 00:00:00')
        else:
            obj = str(obj)
        if dbname in ['oracle', 'informix']:
            return "to_date('%s','yyyy-mm-dd hh24:mi:ss')" % obj
    elif fieldtype == 'time':
        if isinstance(obj, datetime.time):
            obj = obj.strftime('%H:%M:%S')
        else:
            obj = str(obj)
    elif dbname == 'mssql2' and (fieldtype == 'string' or fieldtype == 'text'):
        return "N'%s'" % str(obj).replace("'", "''")
    elif isinstance(fieldtype, SQLCustomType):
        return fieldtype.encoder(obj)
    else:
        obj = str(obj)
    return "'%s'" % obj.replace("'", "''")


def cleanup(text):
    if re.compile('[^0-9a-zA-Z_]').findall(text):
        raise SyntaxError, \
            'only [0-9a-zA-Z_] allowed in table and field names'
    return text


def sqlite3_web2py_extract(lookup, s):
    table = {
        'year': (0, 4),
        'month': (5, 7),
        'day': (8, 10),
        'hour': (11, 13),
        'minute': (14, 16),
        'second': (17, 19),
        }
    try:
        (i, j) = table[lookup]
        return int(s[i:j])
    except:
        return None

def oracle_fix_execute(command, execute):
    args = []
    i = 1
    while True:
        m = oracle_fix.match(command)
        if not m:
            break        
        command = command[:m.start('clob')] + str(i) + command[m.end('clob'):]
        args.append(m.group('clob')[6:-2].replace("''", "'"))
        i += 1
    return execute(command[:-1], args)


def autofields(db, text):
    raise SyntaxError, "work in progress"
    m = re.compile('(?P<i>\w+)')
    (tablename, fields) = text.lower().split(':', 1)
    tablename = tablename.replace(' ', '_')
    newfields = []
    for field in fields.split(','):
        if field.find(' by ') >= 0:
            (items, keys) = field.split(' by ')
        else:
            (items, keys) = (field, '%(id)s')
        items = m.findall(items)
        if not items: break
        keys = m.sub('%(\g<i>)s', keys)
        (requires, notnull, unique) = (None, False, False)
        if items[-1] in ['notnull']:
            (notnull, items) = (True, items[:-1])
        if items[-1] in ['unique']:
            (unique, items) = (True, items[:-1])
        if items[-1] in ['text', 'date', 'datetime', 'time', 'blob', 'upload', 'password',
                         'integer', 'double', 'boolean', 'string']:
            (items, t) = (item[:-1], items[-1])
        elif items[-1] in db.tables:
            t = 'reference %s' % items[-1]
            requires = validators.IS_IN_DB(db, '%s.id' % items[-1], keys)
        else:
            t = 'string'
        name = '_'.join(items)
        if unique:
            if requires:
                raise SyntaxError, "Sorry not supported"
            requires = validators.IS_NOT_IN_DB(db, '%s.%s' % (tablename, name))
        if requires and not notnull:
            requires = validators.IS_NULL_OR(requires)
        label = ' '.join([i.capitalize() for i in items])
        newfields.append(db.Field(name, t, label=label, requires=requires,
                                  notnull=notnull, unique=unique))
    return tablename, newfields

class SQLStorage(dict):

    """
    a dictionary that let you do d['a'] as well as d.a
    """

    def __getitem__(self, key):
        return dict.__getitem__(self, str(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key), value)

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if key in self:
            raise SyntaxError, 'Object exists and cannot be redefined'
        self[key] = value

    def __repr__(self):
        return '<SQLStorage ' + dict.__repr__(self) + '>'


class SQLCallableList(list):

    def __call__(self):
        return copy.copy(self)


# class static_method:
#    """
#    now we can declare static methods in python!
#    """
#    def __init__(self, anycallable): self.__call__ = anycallable


class SQLDB(SQLStorage):

    """
    an instance of this class represents a database connection

    Example:
    
       db=SQLDB('sqlite://test.db')
       db.define_table('tablename',SQLField('fieldname1'),
                                   SQLField('fieldname2'))

    """

    # ## this allows gluon to comunite a folder for this thread

    _folders = {}
    _connection_pools = {}
    _instances = {}

    @staticmethod
    def _set_thread_folder(folder):
        sql_locker.acquire()
        SQLDB._folders[thread.get_ident()] = folder
        sql_locker.release()

    # ## this allows gluon to commit/rollback all dbs in this thread

    @staticmethod
    def close_all_instances(action):
        """ to close cleanly databases in a multithreaded environment """

        sql_locker.acquire()
        pid = thread.get_ident()
        if pid in SQLDB._folders:
            del SQLDB._folders[pid]
        if pid in SQLDB._instances:
            instances = SQLDB._instances[pid]
            while instances:
                instance = instances.pop()
                sql_locker.release()
                action(instance)
                sql_locker.acquire()

                # ## if you want pools recycle this connection
                really = True
                if instance._pool_size:
                    pool = SQLDB._connection_pools[instance._uri]
                    if len(pool) < instance._pool_size:
                        pool.append(instance._connection)
                        really = False
                if really:
                    sql_locker.release()
                    instance._connection.close()
                    sql_locker.acquire()
            del SQLDB._instances[pid]
        sql_locker.release()
        return

    @staticmethod
    def distributed_transaction_commit(*instances):
        if not instances:
            return
        instances = enumerate(instances)
        keys = []
        thread_key = '%s.%i' % (socket.gethostname(),
                                thread.get_ident())
        for (i, db) in instances:
            keys.append('%s.%i' % (thread_key, i))
            if not db._dbname == 'postgres':
                raise SyntaxError, 'only supported by postgresql'
        try:
            for (i, db) in instances:
                db._execute("PREPARE TRANSACTION '%s';" % keys[i])
        except:
            for (i, db) in instances:
                db._execute("ROLLBACK PREPARED '%s';" % keys[i])
            raise Exception, 'failure to commit distributed transaction'
        else:
            for (i, db) in instances:
                db._execute("COMMIT PREPARED '%s';" % keys[i])
        return

    def _pool_connection(self, f):

        # ## deal with particular case first:

        if not self._pool_size:
            self._connection = f()
            return
        uri = self._uri
        sql_locker.acquire()
        if not uri in self._connection_pools:
            self._connection_pools[uri] = []
        if self._connection_pools[uri]:
            self._connection = self._connection_pools[uri].pop()
            sql_locker.release()
        else:
            sql_locker.release()
            self._connection = f()

    def __init__(self, uri='sqlite://dummy.db', pool_size=0, pools=0):
        self._uri = str(uri)
        self._pool_size = pool_size or pools # for backward compatibility
        self['_lastsql'] = ''
        self.tables = SQLCallableList()
        pid = thread.get_ident()

        # Check if there is a folder for this thread else use ''

        sql_locker.acquire()
        if pid in self._folders:
            self._folder = self._folders[pid]
        else:
            self._folder = self._folders[pid] = ''
        sql_locker.release()

        # Creating the folder if it does not exists
        if self._folder:
            if not os.path.exists(self._folder):
                os.mkdir(self._folder)

        # Now connect to database

        if self._uri[:14] == 'sqlite:memory:':
            self._dbname = 'sqlite'
            self._pool_connection(lambda: \
                    sqlite3.Connection(':memory:',
                                       check_same_thread=False))
            self._connection.create_function('web2py_extract', 2,
                    sqlite3_web2py_extract)
            self._cursor = self._connection.cursor()
            self._execute = lambda *a, **b: self._cursor.execute(*a, **b)
        elif self._uri[:9] == 'sqlite://':
            self._dbname = 'sqlite'
            if uri[9] != '/':
                dbpath = os.path.join(self._folder, uri[9:])
                self._pool_connection(lambda : \
                        sqlite3.Connection(dbpath,
                                           check_same_thread=False))
            else:
                self._pool_connection(lambda : \
                        sqlite3.Connection(uri[9:],
                                           check_same_thread=False))
            self._connection.create_function('web2py_extract', 2,
                                             sqlite3_web2py_extract)
            self._cursor = self._connection.cursor()
            self._execute = lambda *a, **b: self._cursor.execute(*a, **b)
        elif self._uri[:8] == 'mysql://':
            self._dbname = 'mysql'
            m = re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$'
                ).match(self._uri[8:])
            if not m:
                raise SyntaxError, "Invalid URI string in SQLDB"
            user = m.group('user')
            if not user:
                raise SyntaxError, 'User required'
            passwd = m.group('passwd')
            if not passwd:
                passwd = ''
            host = m.group('host')
            if not host:
                raise SyntaxError, 'Host name required'
            db = m.group('db')
            if not db:
                raise SyntaxError, 'Database name required'
            port = m.group('port')
            if not port:
                port = '3306'
            charset = m.group('charset')
            if not charset:
                charset = 'utf8'
            self._pool_connection(lambda : MySQLdb.Connection(
                    db=db,
                    user=user,
                    passwd=passwd,
                    host=host,
                    port=int(port),
                    charset=charset,
                    ))
            self._cursor = self._connection.cursor()
            self._execute = lambda *a, **b: self._cursor.execute(*a, **b)
            self._execute('SET FOREIGN_KEY_CHECKS=0;')
            self._execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")
        elif self._uri[:11] == 'postgres://':
            self._dbname = 'postgres'
            m = \
                re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$'
                           ).match(self._uri[11:])
            if not m:
                raise SyntaxError, "Invalid URI string in SQLDB"
            user = m.group('user')
            if not user:
                raise SyntaxError, 'User required'
            passwd = m.group('passwd')
            if not passwd:
                passwd = ''
            host = m.group('host')
            if not host:
                raise SyntaxError, 'Host name required'
            db = m.group('db')
            if not db:
                raise SyntaxError, 'Database name required'
            port = m.group('port')
            if not port:
                port = '5432'
            msg = \
                "dbname='%s' user='%s' host='%s' port=%s password='%s'"\
                 % (db, user, host, port, passwd)
            self._pool_connection(lambda : psycopg2.connect(msg))
            self._connection.set_client_encoding('UTF8')
            self._cursor = self._connection.cursor()
            self._execute = lambda *a, **b: self._cursor.execute(*a, **b)
            query = 'BEGIN;'
            self['_lastsql'] = query
            self._execute(query)
            self._execute("SET CLIENT_ENCODING TO 'UNICODE';")  # ## not completely sure but should work
        elif self._uri[:9] == 'oracle://':
            self._dbname = 'oracle'
            self._pool_connection(lambda : \
                                  cx_Oracle.connect(self._uri[9:]))
            self._cursor = self._connection.cursor()
            self._execute = lambda a: \
                oracle_fix_execute(a,self._cursor.execute)
            self._execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';")
            self._execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")
        elif self._uri[:8] == 'mssql://' or self._uri[:9]\
             == 'mssql2://':

            # ## read: http://bytes.com/groups/python/460325-cx_oracle-utf8

            if self._uri[:8] == 'mssql://':
                skip = 8
                self._dbname = 'mssql'
            elif self._uri[:9] == 'mssql2://':
                skip = 9
                self._dbname = 'mssql2'
            if '@' not in self._uri[skip:]:
                try:
                    m = re.compile('^(?P<dsn>.+)$'
                                   ).match(self._uri[skip:])
                    if not m:
                        raise SyntaxError, 'Parsing has no result'
                    dsn = m.group('dsn')
                    if not dsn:
                        raise SyntaxError, 'DSN required'
                except SyntaxError, e:
                    logging.error('NdGpatch error')
                    raise e
                cnxn = 'DSN=%s' % dsn
            else:
                m = \
                    re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$'
                               ).match(self._uri[skip:])
                if not m:
                    raise SyntaxError, "Invalid URI string in SQLDB"
                user = m.group('user')
                if not user:
                    raise SyntaxError, 'User required'
                passwd = m.group('passwd')
                if not passwd:
                    passwd = ''
                host = m.group('host')
                if not host:
                    raise SyntaxError, 'Host name required'
                db = m.group('db')
                if not db:
                    raise SyntaxError, 'Database name required'
                port = m.group('port')
                if not port:
                    port = '1433'

                # Driver={SQL Server};description=web2py;server=A64X2;uid=web2py;database=web2py_test;network=DBMSLPCN

                cnxn = \
                    'Driver={SQL Server};server=%s;database=%s;uid=%s;pwd=%s'\
                     % (host, db, user, passwd)
            self._pool_connection(lambda : pyodbc.connect(cnxn))
            self._cursor = self._connection.cursor()
            if self._uri[:8] == 'mssql://':
                self._execute = lambda *a, **b: self._cursor.execute(*a, **b)
            elif self._uri[:9] == 'mssql2://':
                self._execute = lambda a: \
                    self._cursor.execute(unicode(a, 'utf8'))
        elif self._uri[:11] == 'firebird://':
            self._dbname = 'firebird'
            m = \
                re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)(\?set_encoding=(?P<charset>\w+))?$'
                           ).match(self._uri[11:])
            if not m:
                raise SyntaxError, "Invalid URI string in SQLDB"
            user = m.group('user')
            if not user:
                raise SyntaxError, 'User required'
            passwd = m.group('passwd')
            if not passwd:
                passwd = ''
            host = m.group('host')
            if not host:
                raise SyntaxError, 'Host name required'
            db = m.group('db')
            if not db:
                raise SyntaxError, 'Database name required'
            port = m.group('port')
            if not port:
                port = '3050'
            charset = m.group('charset')
            if not charset:
                charset = 'UTF8'
            self._pool_connection(lambda : \
                                  kinterbasdb.connect(dsn='%s:%s'
                                   % (host, db), user=user,
                                  password=passwd))
            self._cursor = self._connection.cursor()
            self._execute = lambda *a, **b: self._cursor.execute(*a, **b)
            if charset != 'None':
                self._execute('SET NAMES %s;' % charset)
        elif self._uri[:11] == 'informix://':
            self._dbname = 'informix'
            m = \
                re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$'
                           ).match(self._uri[11:])
            if not m:
                raise SyntaxError, "Invalid URI string in SQLDB"
            user = m.group('user')
            if not user:
                raise SyntaxError, 'User required'
            passwd = m.group('passwd')
            if not passwd:
                passwd = ''
            host = m.group('host')
            if not host:
                raise SyntaxError, 'Host name required'
            db = m.group('db')
            if not db:
                raise SyntaxError, 'Database name required'
            port = m.group('port')
            if not port:
                port = '3050'
            self._pool_connection(lambda : informixdb.connect('%s@%s'
                                   % (db, host), user=user,
                                  password=passwd))
            self._cursor = self._connection.cursor()
            self._execute = lambda a: self._cursor.execute(a[:-1])
        elif self._uri[:4] == 'db2:':
            self._dbname, cnxn = self._uri.split(':', 1)
            self._pool_connection(lambda : pyodbc.connect(cnxn))
            self._cursor = self._connection.cursor()
            self._execute = lambda a: self._cursor.execute(a[:-1])
        elif self._uri[:5] == 'jdbc:':
            self._dbname = self._uri.split(':')[1]
            if self._dbname == 'sqlite':
                if uri[14] != '/':
                    dbpath = os.path.join(self._folder, uri[14:])
                else:
                    dbpath = os.path.join(self._folder, uri[14:])
                self._pool_connection(lambda : zxJDBC.connect(uri[:14] + dbpath))
                self._connection.create_function('web2py_extract', 2,
                       sqlite3_web2py_extract)
            else:
                raise SyntaxError, "sorry only sqlite on jdbc for now"
            self._cursor = self._connection.cursor()
            self._execute = lambda a: self._cursor.execute(a[:-1])
        elif self._uri == 'None':


            class Dummy:

                lastrowid = 1

                def __getattr__(self, value):
                    return lambda *a, **b: ''


            self._dbname = 'sqlite'
            self._connection = Dummy()
            self._cursor = Dummy()
            self._execute = lambda a: []
        else:
            raise SyntaxError, 'database type not supported'
        self._translator = SQL_DIALECTS[self._dbname]

        # ## register this instance of SQLDB

        sql_locker.acquire()
        if not pid in self._instances:
            self._instances[pid] = []
        self._instances[pid].append(self)
        sql_locker.release()
        pass

    def define_table(
        self,
        tablename,
        *fields,
        **args
        ):
        if not fields and tablename.count(':'):
            (tablename, fields) = autofields(self, tablename)
        if not 'migrate' in args:
            args['migrate'] = True
        if args.keys() != ['migrate']:
            raise SyntaxError, 'invalid table attribute'
        tablename = cleanup(tablename)
        if tablename in dir(self) or tablename[0] == '_':
            raise SyntaxError, 'invalid table name'
        if tablename in self.tables:
            raise SyntaxError, 'table already defined'
        t = self[tablename] = SQLTable(self, tablename, *fields)
        if self._uri == 'None':
            args['migrate'] = False
            return t
        sql_locker.acquire()
        try:
            query = t._create(migrate=args['migrate'])
        except BaseException, e:
            sql_locker.release()
            raise e
        sql_locker.release()
        self.tables.append(tablename)
        return t

    def __call__(self, where=None):
        return SQLSet(self, where)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def executesql(self, query):
        self['_lastsql'] = query
        self._execute(query)
        return self._cursor.fetchall()

    def _update_referenced_by(self, other):
        for tablename in self.tables:
            by = self[tablename]._referenced_by
            by[:] = [item for item in by if not item[0] == other]

    def __getstate__(self):
        return dict()

    def export_to_csv_file(self, ofile):
        for table in self.tables:
            ofile.write('TABLE %s\r\n' % table)
            self(self[table].id > 0).select().export_to_csv_file(ofile)
            ofile.write('''\r
\r
''')
        ofile.write('END')

    def import_from_csv_file(self, ifile, id_map={}):
        while True:
            line = ifile.readline()
            if line.strip() == 'END':
                return
            if not line.strip():
                continue
            if not line[:6] == 'TABLE ' or not line[6:].strip()\
                 in self.tables:
                raise SyntaxError, 'invalid file format'
            table = line[6:].strip()
            self[table].import_from_csv_file(ifile, id_map)


def unpickle_SQLDB(state):
    logging.warning('unpickling SQLDB objects is experimental')
    db = SQLDB(state['uri'])
    for (k, d) in state['tables']:
        db.define_table(k, *[SQLField(**i) for i in d],
                        **dict(migrate=False))
    return db


def pickle_SQLDB(db):
    logging.warning('pickling SQLDB objects is experimental')
    tables = []
    for k in db.values():
        if not isinstance(k, SQLTable):
            continue
        fields = []
        for f in k.values():
            if not isinstance(f, SQLField) or f.name == 'id':
                continue
            fields.append(dict(
                fieldname=f.name,
                type=f.type,
                length=f.length,
                default=f.default,
                required=f.required,
                requires=f.requires,
                ondelete=f.ondelete,
                notnull=f.notnull,
                unique=f.notnull,
                uploadfield=f.uploadfield,
                ))
        tables.append((k._tablename, fields))
    return (unpickle_SQLDB, (dict(uri=db._uri, tables=tables), ))


copy_reg.pickle(SQLDB, pickle_SQLDB)


class SQLALL(object):

    def __init__(self, table):
        self.table = table

    def __str__(self):
        s = ['%s.%s' % (self.table._tablename, name) for name in
             self.table.fields]
        return ', '.join(s)


class SQLJoin(object):

    def __init__(self, table, query):
        self.table = table
        self.query = query

    def __str__(self):
        return '%s ON %s' % (self.table, self.query)


def is_integer(x):
    try:
        long(x)
    except ValueError:
        return False
    except TypeError:
        return False
    return True


class SQLTable(dict):

    """
    an instance of this class represents a database table
    Example:
    
    db=SQLDB(...)
    db.define_table('users',SQLField('name'))
    db.users.insert(name='me') # print db.users._insert(...) to see SQL
    db.users.drop()
    """

    def __init__(
        self,
        db,
        tablename,
        *fields
        ):
        new_fields = []
        for field in fields:
            if isinstance(field, SQLField):
                new_fields.append(field)
            elif isinstance(field, SQLTable):
                new_fields += [copy.copy(field[f]) for f in
                               field.fields if f != 'id']
            else:
                raise SyntaxError, \
                    'define_table argument is not a SQLField'
        fields = new_fields
        self._db = db
        self._tablename = tablename
        self.fields = SQLCallableList()
        self._referenced_by = []
        fields = list(fields)
        fields.insert(0, SQLField('id', 'id'))
        for field in fields:
            self.fields.append(field.name)
            self[field.name] = field
            field._tablename = self._tablename
            field._table = self
            field._db = self._db
        self.ALL = SQLALL(self)

    def _filter_fields(self, record, id=False):
        return dict([(k, v) for (k, v) in record.items() if k
                     in self.fields and (id or k != 'id')])

    def __getitem__(self, key):
        if is_integer(key):
            rows = self._db(self.id == key).select()
            if rows:
                return rows[0]
            return None
        else:
            return dict.__getitem__(self, str(key))

    def __setitem__(self, key, value):
        if is_integer(key):
            if key == 0:
                self.insert(**self._filter_fields(value))
            elif not self._db(self.id
                               == key).update(**self._filter_fields(value)):
                raise SyntaxError, 'No such record'
        else:
            dict.__setitem__(self, str(key), value)

    def __delitem__(self, key):
        if not is_integer(key) or not self._db(self.id == key).delete():
            raise SyntaxError, 'No such record'

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if key in self:
            raise SyntaxError, 'Object exists and cannot be redefined'
        self[key] = value

    def __repr__(self):
        return '<SQLSTable ' + dict.__repr__(self) + '>'

    def __str__(self):
        if self.get('_ot', None):
            return '%s AS %s' % (self._ot, self._tablename)
        return self._tablename

    def with_alias(self, alias):
        other = copy.copy(self)
        other['_ot'] = other._tablename
        other['ALL'] = SQLALL(other)
        other['_tablename'] = alias
        for fieldname in other.fields:
            other[fieldname] = copy.copy(other[fieldname])
            other[fieldname]._tablename = alias
        self._db[alias] = self
        return other

    def _create(self, migrate=True):
        fields = []
        sql_fields = {}
        sql_fields_aux = {}
        for k in self.fields:
            field = self[k]
            if field.type[:9] == 'reference':
                referenced = field.type[10:].strip()
                if not referenced:
                    raise SyntaxError, 'SQLTable: reference to nothing!'
                if not referenced in self._db:
                    raise SyntaxError, 'SQLTable: table does not exist'
                referee = self._db[referenced]
                ftype = self._db._translator[field.type[:9]]\
                     % dict(table_name=self._tablename,
                            field_name=field.name,
                            foreign_key=referenced + '(id)',
                            on_delete_action=field.ondelete)
                if self._tablename in referee.fields:  # ## THIS IS OK
                    raise SyntaxError, \
                        'SQLField: table name has same name as a field in referenced table'
                self._db[referenced]._referenced_by.append((self._tablename,
                        field.name))
            elif isinstance(field.type,SQLCustomType):
                ftype = field.type.native or field.type.type
            elif not field.type in self._db._translator:
                raise SyntaxError, 'SQLField: unkown field type'
            else:
                ftype = self._db._translator[field.type]\
                     % dict(length=field.length)
            if not field.type[:9] in ['id', 'reference']:
                if field.notnull:
                    ftype += ' NOT NULL'
                if field.unique:
                    ftype += ' UNIQUE'
            sql_fields[field.name] = ftype
            if field.default:
                sql_fields_aux[field.name] = ftype.replace('NOT NULL',
                        self._db._translator['notnull']
                         % dict(default=sql_represent(field.default,
                        field.type, self._db._dbname)))
            else:
                sql_fields_aux[field.name] = ftype
            fields.append('%s %s' % (field.name, ftype))
        other = ';'
        if self._db._dbname == 'mysql':
            fields.append('PRIMARY KEY(id)')
            other = ' ENGINE=InnoDB CHARACTER SET utf8;'
        fields = ',\n\t'.join(fields)
        query = '''CREATE TABLE %s(\n\t%s\n)%s''' % \
           (self._tablename, fields, other)

        if self._db._uri[:10] == 'sqlite:///':
            dbpath = self._db._uri[9:self._db._uri.rfind('/')]
        else:
            dbpath = self._db._folder

        if not migrate:
            self._dbt = None
            return query
        elif self._db._uri[:14] == 'sqlite:memory:':
            self._dbt = None
        elif isinstance(migrate, str):
            self._dbt = os.path.join(dbpath, migrate)
        else:
            self._dbt = os.path.join(dbpath, '%s_%s.table' \
                     % (hash(self._db._uri), self._tablename))
        if self._dbt:
            self._logfilename = os.path.join(dbpath, 'sql.log')
            logfile = open(self._logfilename, 'a')
        else:
            logfile = None
        if not self._dbt or not os.path.exists(self._dbt):
            if self._dbt:
                logfile.write('timestamp: %s\n'
                               % datetime.datetime.today().isoformat())
                logfile.write(query + '\n')
            self._db['_lastsql'] = query
            self._db._execute(query)
            if self._db._dbname in ['oracle']:
                t = self._tablename
                self._db._execute('CREATE SEQUENCE %s_sequence START WITH 1 INCREMENT BY 1 NOMAXVALUE;'
                                   % t)
                self._db._execute('CREATE OR REPLACE TRIGGER %s_trigger BEFORE INSERT ON %s FOR EACH ROW BEGIN SELECT %s_sequence.nextval INTO :NEW.id FROM DUAL; END;\n'
                                   % (t, t, t))
            elif self._db._dbname == 'firebird':
                t = self._tablename
                self._db._execute('create generator GENID_%s;' % t)
                self._db._execute('set generator GENID_%s to 0;' % t)
                self._db._execute('''create trigger trg_id_%s for %s active before insert position 0 as\nbegin\nif(new.id is null) then\nbegin\nnew.id = gen_id(GENID_%s, 1);\nend\nend;
''' % (t, t, t))
            self._db.commit()
            if self._dbt:
                tfile = open(self._dbt, 'w')
                cPickle.dump(sql_fields, tfile)
                tfile.close()
            if self._dbt:
                logfile.write('success!\n')
        else:
            tfile = open(self._dbt, 'r')
            sql_fields_old = cPickle.load(tfile)
            tfile.close()
            if sql_fields != sql_fields_old:
                self._migrate(sql_fields, sql_fields_old,
                              sql_fields_aux, logfile)
        return query

    def _migrate(
        self,
        sql_fields,
        sql_fields_old,
        sql_fields_aux,
        logfile,
        ):
        keys = sql_fields.keys()
        for key in sql_fields_old:
            if not key in keys:
                keys.append(key)
        for key in keys:
            if not key in sql_fields_old:
                query = ['ALTER TABLE %s ADD %s %s;' % (self._tablename,
                        key, sql_fields_aux[key].replace(', ', ', ADD '))]
            elif self._db._dbname == 'sqlite':
                query = None
            elif not key in sql_fields:
                query = ['ALTER TABLE %s DROP COLUMN %s;' % (self._tablename, key)]
            elif sql_fields[key] != sql_fields_old[key] and \
                 not (self[key].type[:9]=='reference' and \
                      sql_fields[key][:4]=='INT,' and \
                      sql_fields_old[key][:13]=='INT NOT NULL,'):

                # ## FIX THIS WHEN DIFFRENCES IS ONLY IN DEFAULT
                # 2

                t = self._tablename
                tt = sql_fields_aux[key].replace(', ', ', ADD ')
                query = ['ALTER TABLE %s ADD %s__tmp %s;' % (t, key, tt),
                         'UPDATE %s SET %s__tmp=%s;' % (t, key, key),
                         'ALTER TABLE %s DROP COLUMN %s;' % (t, key),
                         'ALTER TABLE %s ADD %s %s;' % (t, key, tt),
                         'UPDATE %s SET %s=%s__tmp;' % (t, key, key),
                         'ALTER TABLE %s DROP COLUMN %s__tmp;' % (t, key)]
            else:
                query = None

            if query:
                logfile.write('timestamp: %s\n'
                               % datetime.datetime.today().isoformat())
                self._db['_lastsql'] = '\n'.join(query)
                for sub_query in query:
                    logfile.write(sub_query + '\n')
                    self._db._execute(sub_query)
                    if self._db._dbname in ['mysql', 'oracle']:
                        self._db.commit()
                    logfile.write('success!\n')
                if key in sql_fields:
                    sql_fields_old[key] = sql_fields[key]
                else:
                    del sql_fields_old[key]
        tfile = open(self._dbt, 'w')
        cPickle.dump(sql_fields_old, tfile)
        tfile.close()

    def create(self):

        # nothing to do, here for backward compatility

        pass

    def _drop(self, mode = None):
        t = self._tablename
        c = mode or ''
        if self._db._dbname in ['oracle']:
            return ['DROP TABLE %s %s;' % (t, c), 'DROP SEQUENCE %s_sequence;'
                     % t]
        elif self._db._dbname == 'firebird':
            return ['DROP TABLE %s %s;' % (t, c), 'DROP GENERATOR GENID_%s;'
                     % t]
        return ['DROP TABLE %s;' % t]

    def drop(self, mode = None):
        if self._dbt:
            logfile = open(self._logfilename, 'a')
        queries = self._drop(mode = mode)
        self._db['_lastsql'] = '\n'.join(queries)
        for query in queries:
            if self._dbt:
                logfile.write(query + '\n')
            self._db._execute(query)
        self._db.commit()
        del self._db[self._tablename]
        del self._db.tables[self._db.tables.index(self._tablename)]
        self._db._update_referenced_by(self._tablename)
        if self._dbt:
            os.unlink(self._dbt)
            logfile.write('success!\n')

    def _insert(self, **fields):
        (fs, vs) = ([], [])
        if [key for key in fields if not key in self.fields]:
            raise SyntaxError, 'invalid field name'
        for fieldname in self.fields:
            if fieldname == 'id':
                continue
            field = self[fieldname]
            (ft, fd) = (field.type, field._db._dbname)
            if fieldname in fields:
                fs.append(fieldname)
                value = fields[fieldname]
                try:
                    vs.append(sql_represent(value.id, ft, fd))
                except:
                    vs.append(sql_represent(value, ft, fd))
            elif field.default != None:
                fs.append(fieldname)
                vs.append(sql_represent(field.default, ft, fd))
            elif field.required is True:
                raise SyntaxError,'SQLTable: missing required field: %s'%field 
        sql_f = ', '.join(fs)
        sql_v = ', '.join(vs)
        sql_t = self._tablename
        return 'INSERT INTO %s(%s) VALUES (%s);' % (sql_t, sql_f, sql_v)

    def insert(self, **fields):
        query = self._insert(**fields)
        self._db['_lastsql'] = query
        self._db._execute(query)
        if self._db._dbname == 'sqlite':
            id = self._db._cursor.lastrowid
        elif self._db._dbname == 'postgres':
            self._db._execute("select currval('%s_id_Seq')"
                               % self._tablename)
            id = int(self._db._cursor.fetchone()[0])
        elif self._db._dbname == 'mysql':
            self._db._execute('select last_insert_id();')
            id = int(self._db._cursor.fetchone()[0])
        elif self._db._dbname in ['oracle']:
            t = self._tablename
            self._db._execute('SELECT %s_sequence.currval FROM dual;'
                               % t)
            id = int(self._db._cursor.fetchone()[0])
        elif self._db._dbname == 'mssql' or self._db._dbname\
             == 'mssql2':
            self._db._execute('SELECT @@IDENTITY;')
            id = int(self._db._cursor.fetchone()[0])
        elif self._db._dbname == 'firebird':
            self._db._execute('SELECT gen_id(GENID_%s, 0) FROM rdb$database'
                               % self._tablename)
            id = int(self._db._cursor.fetchone()[0])
        elif self._db._dbname == 'informix':
            self._db._execute('SELECT LOCAL_SQLCA^.sqlerrd[1]')
            id = int(self._db._cursor.fetchone()[0])
        elif self._db._dbname == 'db2':
            self._db._execute('SELECT DISTINCT IDENTITY_VAL_LOCAL() FROM %s;'%self._tablename)
            id = int(self._db._cursor.fetchone()[0])
        else:
            id = None
        return id

    def import_from_csv_file(
        self,
        csvfile,
        id_map=None,
        null='<NULL>',
        unique='uuid',
        ):
        """
        import records from csv file. Column headers must have same names as
        table fields. field 'id' is ignored. If column names read 'table.file'
        the 'table.' prefix is ignored.
        'unique' argument is a field which must be unique (typically a uuid field)
        """

        reader = csv.reader(csvfile)
        colnames = None
        if isinstance(id_map, dict):
            if not self._tablename in id_map:
                id_map[self._tablename] = {}
            id_map_self = id_map[self._tablename]

        def fix(field, value, id_map):
            if value == null:
                value = None
            elif id_map and field.type[:9] == 'reference':
                try:
                    value = id_map[field.type[9:].strip()][value]
                except KeyError:
                    pass
            return (field.name, value)

        for line in reader:
            if not line:
                break
            if not colnames:
                colnames = [x[x.find('.') + 1:] for x in line]
                c = [i for i in xrange(len(line)) if colnames[i] != 'id']
                cid = [i for i in xrange(len(line)) if colnames[i] == 'id']
                if cid:
                    cid = cid[0]
            else:
                items = [fix(self[colnames[i]], line[i], id_map) for i in c]
                if not unique or unique not in colnames:
                    new_id = self.insert(**dict(items))
                else:
                    # Validation. Check for duplicate of 'unique' &, if present, update instead of insert.
                    for i in c:
                        if colnames[i] == unique:
                            _unique = line[i]
                    if self._db(self._db[self][unique]==_unique).count():
                        self._db(self[unique]==_unique).update(**dict(items))
                    else:
                        new_id = self.insert(**dict(items))
                if id_map and cid != []:
                    id_map_self[line[cid]] = new_id

    def on(self, query):
        return SQLJoin(self, query)

    def _truncate(self, mode = None):
        t = self._tablename
        c = mode or ''
        if self._db._dbname == 'sqlite':
            return ['DELETE FROM %s;' % t,
                    "DELETE FROM sqlite_sequence WHERE name='%s';" % t]
        return ['TRUNCATE TABLE %s %s;' % (t, c)]

    def truncate(self, mode = None):
        if self._dbt:
            logfile = open(self._logfilename, 'a')
        queries = self._truncate(mode = mode)
        self._db['_lastsql'] = '\n'.join(queries)
        for query in queries:
            if self._dbt:
                logfile.write(query + '\n')
            self._db._execute(query)
        self._db.commit()
        if self._dbt:
            logfile.write('success!\n')

class SQLXorable(object):

    def __init__(
        self,
        name,
        type='string',
        db=None,
        ):
        (self.name, self.type, self._db) = (name, type, db)

    def __str__(self):
        return self.name

    def __or__(self, other):  # for use in sortby
        return SQLXorable(str(self) + ', ' + str(other), None, None)

    def __invert__(self):
        return SQLXorable(str(self) + ' DESC', None, None)

    # for use in SQLQuery

    def __eq__(self, value):
        return SQLQuery(self, '=', value)

    def __ne__(self, value):
        return SQLQuery(self, '<>', value)

    def __lt__(self, value):
        return SQLQuery(self, '<', value)

    def __le__(self, value):
        return SQLQuery(self, '<=', value)

    def __gt__(self, value):
        return SQLQuery(self, '>', value)

    def __ge__(self, value):
        return SQLQuery(self, '>=', value)

    def like(self, value):
        return SQLQuery(self, ' LIKE ', value)

    def belongs(self, value):
        return SQLQuery(self, ' IN ', value)

    # for use in both SQLQuery and sortby

    def __add__(self, other):
        return SQLXorable('(%s+%s)' % (self, sql_represent(other,
                          self.type, self._db._dbname)), self.type,
                          self._db)

    def __sub__(self, other):
        return SQLXorable('(%s-%s)' % (self, sql_represent(other,
                          self.type, self._db._dbname)), self.type,
                          self._db)

    def __mul__(self, other):
        return SQLXorable('(%s*%s)' % (self, sql_represent(other,
                          self.type, self._db._dbname)), self.type,
                          self._db)

    def __div__(self, other):
        return SQLXorable('(%s/%s)' % (self, sql_represent(other,
                          self.type, self._db._dbname)), self.type,
                          self._db)


class SQLCustomType:
    def __init__(self, type='string', native=None, encoder=None, decoder=None):
        self.type = type
        self.native = native
        self.encoder = encoder or (lambda x: x)
        self.decoder = decoder or (lambda x: x)
    def __getslice__(self,a=0,b=100):
        return None
    def __getitem__(self,i):
        return None

class SQLField(SQLXorable):

    """
    an instance of this class represents a database field

    example:

    a=SQLField(name,'string',length=32,required=False,default=None,requires=IS_NOT_EMPTY(),notnull=False,unique=False,uploadfield=True,widget=None,label=None,comment=None,writable=True,readable=True,update=None,authorize=None,autodelete=False,represent=None)
    
    to be used as argument of SQLDB.define_table

    allowed field types:
    string, boolean, integer, double, text, blob, 
    date, time, datetime, upload, password

    strings must have a length or 32 by default.
    fields should have a default or they will be required in SQLFORMs
    the requires argument is used to validate the field input in SQLFORMs

    """

    def __init__(
        self,
        fieldname,
        type='string',
        length=32,
        default=None,
        required=False,
        requires=sqlhtml_validators,
        ondelete='CASCADE',
        notnull=False,
        unique=False,
        uploadfield=True,
        widget=None,
        label=None,
        comment=None,
        writable=True,
        readable=True,
        update=None,
        authorize=None,
        autodelete=False,
        represent=None,
        ):

        self.name = fieldname = cleanup(fieldname)
        if fieldname in dir(SQLTable) or fieldname[0] == '_':
            raise SyntaxError, 'SQLField: invalid field name'
        if isinstance(type, SQLTable):
            type = 'reference ' + type._tablename
        if not length and type == 'string':
            type = 'text'
        elif not length and type == 'password':
            length = 32
        self.type = type  # 'string', 'integer'
        if type == 'upload':
            length = 64
        self.length = length  # the length of the string
        self.default = default  # default value for field
        self.required = required  # is this field required
        self.ondelete = ondelete.upper()  # this is for reference fields only
        self.notnull = notnull
        self.unique = unique
        self.uploadfield = uploadfield
        self.widget = widget
        self.label = label
        self.comment = comment
        self.writable = writable
        self.readable = readable
        self.update = update
        self.authorize = authorize
        self.autodelete = autodelete
        self.represent = represent
        self.isattachment = True
        if self.label == None:
            self.label = ' '.join([x.capitalize() for x in
                                  fieldname.split('_')])
        if requires == sqlhtml_validators:
            requires = sqlhtml_validators(type, length)
        elif requires is None:
            requires = []
        self.requires = requires  # list of validators

    def formatter(self, value):
        if value is None or not self.requires:
            return value
        if not isinstance(self.requires, (list, tuple)):
            requires = [self.requires]
        elif isinstance(self.requires, tuple):
            requires = list(self.requires)
        else:
            requires = copy.copy(self.requires)
        requires.reverse()
        for item in requires:
            if hasattr(item, 'formatter'):
                value = item.formatter(value)
        return value

    def validate(self, value):
        if not self.requires:
            return (value, None)
        requires = self.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                return (value, error)
        return (value, None)

    def lower(self):
        s = self._db._translator['lower'] % dict(field=str(self))
        return SQLXorable(s, 'string', self._db)

    def upper(self):
        s = self._db._translator['upper'] % dict(field=str(self))
        return SQLXorable(s, 'string', self._db)

    def year(self):
        s = self._db._translator['extract'] % dict(name='year',
                field=str(self))
        return SQLXorable(s, 'integer', self._db)

    def month(self):
        s = self._db._translator['extract'] % dict(name='month',
                field=str(self))
        return SQLXorable(s, 'integer', self._db)

    def day(self):
        s = self._db._translator['extract'] % dict(name='day',
                field=str(self))
        return SQLXorable(s, 'integer', self._db)

    def hour(self):
        s = self._db._translator['extract'] % dict(name='hour',
                field=str(self))
        return SQLXorable(s, 'integer', self._db)

    def minutes(self):
        s = self._db._translator['extract'] % dict(name='minute',
                field=str(self))
        return SQLXorable(s, 'integer', self._db)

    def seconds(self):
        s = self._db._translator['extract'] % dict(name='second',
                field=str(self))
        return SQLXorable(s, 'integer', self._db)

    def count(self):
        return SQLXorable('COUNT(%s)' % str(self), 'integer', self._db)

    def sum(self):
        return SQLXorable('SUM(%s)' % str(self), 'integer', self._db)

    def max(self):
        return SQLXorable('MAX(%s)' % str(self), 'integer', self._db)

    def min(self):
        return SQLXorable('MIN(%s)' % str(self), 'integer', self._db)

    def __getslice__(self, start, stop):
        if start < 0 or stop < start:
            raise SyntaxError, 'not supported'
        d = dict(field=str(self), pos=start + 1, length=stop - start)
        s = self._db._translator['substring'] % d
        return SQLXorable(s, 'string', self._db)

    def __str__(self):
        return '%s.%s' % (self._tablename, self.name)


SQLDB.Field = SQLField  # necessary in gluon/globals.py session.connect
SQLDB.Table = SQLTable  # necessary in gluon/globals.py session.connect


class SQLQuery(object):

    """
    a query object necessary to define a set.
    t can be stored or can be passed to SQLDB.__call__() to obtain a SQLSet

    Example:
    query=db.users.name=='Max'
    set=db(query)
    records=set.select()
    """

    def __init__(
        self,
        left,
        op=None,
        right=None,
        ):
        if op is None and right is None:
            self.sql = left
        elif right is None:
            if op == '=':
                self.sql = '%s %s' % (left,
                        left._db._translator['is null'])
            elif op == '<>':
                self.sql = '%s %s' % (left,
                        left._db._translator['is not null'])
            else:
                raise SyntaxError, 'do not know what to do'
        elif op == ' IN ':
            if isinstance(right, str):
                self.sql = '%s%s(%s)' % (left, op, right[:-1])
            elif hasattr(right, '__iter__'):
                r = ','.join([sql_represent(i, left.type, left._db)
                             for i in right])
                self.sql = '%s%s(%s)' % (left, op, r)
            else:
                raise SyntaxError, 'do not know what to do'
        elif isinstance(right, (SQLField, SQLXorable)):
            self.sql = '%s%s%s' % (left, op, right)
        else:
            right = sql_represent(right, left.type, left._db._dbname)
            self.sql = '%s%s%s' % (left, op, right)

    def __and__(self, other):
        return SQLQuery('(%s AND %s)' % (self, other))

    def __or__(self, other):
        return SQLQuery('(%s OR %s)' % (self, other))

    def __invert__(self):
        return SQLQuery('(NOT %s)' % self)

    def __str__(self):
        return self.sql


regex_tables = re.compile('(?P<table>[a-zA-Z]\w*)\.')
regex_quotes = re.compile("'[^']*'")


def parse_tablenames(text):
    text = regex_quotes.sub('', text)
    while 1:
        i = text.find('IN (SELECT ')
        if i == -1:
            break
        (k, j, n) = (1, i + 11, len(text))
        while k and j < n:
            c = text[j]
            if c == '(':
                k += 1
            elif c == ')':
                k -= 1
            j += 1
        text = text[:i] + text[j + 1:]
    items = regex_tables.findall(text)
    tables = {}
    for item in items:
        tables[item] = True
    return tables.keys()


def xorify(orderby):
    if not orderby:
        return None
    orderby2 = orderby[0]
    for item in orderby[1:]:
        orderby2 = orderby2 | item
    return orderby2


class SQLSet(object):

    """
    sn SQLSet represents a set of records in the database,
    the records are identified by the where=SQLQuery(...) object.
    normally the SQLSet is generated by SQLDB.__call__(SQLQuery(...))

    given a set, for example
       set=db(db.users.name=='Max')
    you can:
       set.update(db.users.name='Massimo')
       set.delete() # all elements in the set
       set.select(orderby=db.users.id,groupby=db.users.name,limitby=(0,10))
    and take subsets:
       subset=set(db.users.id<5)
    """

    def __init__(self, db, where=''):
        self._db = db
        self._tables = []

        # find out wchich tables are involved

        self.sql_w = str(where or '')

        # print self.sql_w

        self._tables = parse_tablenames(self.sql_w)

        # print self._tables

    def __call__(self, where):
        if self.sql_w:
            return SQLSet(self._db, SQLQuery(self.sql_w) & where)
        else:
            return SQLSet(self._db, where)

    def _select(self, *fields, **attributes):
        valid_attributes = [
            'orderby',
            'groupby',
            'limitby',
            'required',
            'cache',
            'default',
            'requires',
            'left',
            'distinct',
            'having',
            ]
        if [key for key in attributes if not key
             in valid_attributes]:
            raise SyntaxError, 'invalid select attribute'

        # ## if not fields specified take them all from the requested tables

        if not fields:
            fields = [self._db[table].ALL for table in self._tables]
        sql_f = ', '.join([str(f) for f in fields])
        tablenames = parse_tablenames(self.sql_w + ' ' + sql_f)
        if len(tablenames) < 1:
            raise SyntaxError, 'SQLSet: no tables selected'
        self.colnames = [c.strip() for c in sql_f.split(', ')]
        if self.sql_w:
            sql_w = ' WHERE ' + self.sql_w
        else:
            sql_w = ''
        sql_o = ''
        sql_s = 'SELECT'
        if attributes.get('distinct', False):
            sql_s += ' DISTINCT'
        if attributes.get('left', False):
            join = attributes['left']
            command = self._db._translator['left join']
            if not isinstance(join, (tuple, list)):
                join = [join]
            joint = [t._tablename for t in join if not isinstance(t,
                     SQLJoin)]
            joinon = [t for t in join if isinstance(t, SQLJoin)]
            joinont = [t.table._tablename for t in joinon]
            excluded = [t for t in tablenames if not t in joint
                         + joinont]
            sql_t = ', '.join(excluded)
            if joint:
                sql_t += ' %s %s' % (command, ', '.join(joint))
            for t in joinon:
                sql_t += ' %s %s' % (command, str(t))
        else:
            sql_t = ', '.join(tablenames)
        if attributes.get('groupby', False):
            sql_o += ' GROUP BY %s' % attributes['groupby']
            if attributes.get('having', False):
                sql_o += ' HAVING %s' % attributes['having']
        orderby = attributes.get('orderby', False)
        if orderby:
            if isinstance(orderby, (list, tuple)):
                orderby = xorify(orderby)
            if str(orderby) == '<random>':
                sql_o += ' ORDER BY %s' % self._db._translator['random']
            else:
                sql_o += ' ORDER BY %s' % orderby
        if attributes.get('limitby', False):
            # oracle does not support limitby
            (lmin, lmax) = attributes['limitby']
            if self._db._dbname in ['oracle']:
                if not attributes.get('orderby', None):
                    sql_o += ' ORDER BY %s' % ', '.join([t + '.id'
                            for t in tablenames])
                if len(sql_w) > 1:
                    sql_w_row = sql_w + ' AND w_row > %i' % lmin
                else:
                    sql_w_row = 'WHERE w_row > %i' % lmin
                return '%s %s FROM (SELECT w_tmp.*, ROWNUM w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNUM<=%i) %s %s;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, sql_w_row)
                #return '%s %s FROM (SELECT w_tmp.*, ROWNUM w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNUM<=%i) %s WHERE w_row>%i;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, lmin)
                #return '%s %s FROM (SELECT *, ROWNUM w_row FROM (SELECT %s FROM %s%s%s) WHERE ROWNUM<=%i) WHERE w_row>%i;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, lmin)
            elif self._db._dbname == 'mssql' or \
                 self._db._dbname == 'mssql2':
                if not attributes.get('orderby', None):
                    sql_o += ' ORDER BY %s' % ', '.join([t + '.id'
                            for t in tablenames])
                sql_s += ' TOP %i' % lmax
            elif self._db._dbname == 'firebird':
                if not attributes.get('orderby', None):
                    sql_o += ' ORDER BY %s' % ', '.join([t + '.id'
                            for t in tablenames])
                sql_s += ' FIRST %i SKIP %i' % (lmax - lmin, lmin)
            elif self._db._dbname == 'db2':
                if not attributes.get('orderby', None):
                    sql_o += ' ORDER BY %s' % ', '.join([t + '.id'
                            for t in tablenames])
                sql_o += ' FETCH FIRST %i ROWS ONLY' % lmax
            else:
                sql_o += ' LIMIT %i OFFSET %i' % (lmax - lmin, lmin)
        return '%s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w,
                sql_o)

    def select(self, *fields, **attributes):
        """
        Always returns a SQLRows object, even if it may be empty
        """

        def response(query):
            self._db['_lastsql'] = query
            self._db._execute(query)
            return self._db._cursor.fetchall()

        if not attributes.get('cache', None):
            query = self._select(*fields, **attributes)
            r = response(query)
        else:
            (cache_model, time_expire) = attributes['cache']
            del attributes['cache']
            query = self._select(*fields, **attributes)
            key = self._db._uri + '/' + query
            r = cache_model(key, lambda : response(query), time_expire)
        if self._db._dbname in ['mssql', 'mssql2', 'db2']:
            r = r[(attributes.get('limitby', None) or (0,))[0]:]
        return SQLRows(self._db, r, *self.colnames)

    def _count(self):
        return self._select('count(*)')

    def count(self):
        return self.select('count(*)').response[0][0]

    def _delete(self):
        if len(self._tables) != 1:
            raise SyntaxError, \
                'SQLSet: unable to determine what to delete'
        tablename = self._tables[0]
        if self.sql_w:
            sql_w = ' WHERE ' + self.sql_w
        else:
            sql_w = ''
        return 'DELETE FROM %s%s;' % (tablename, sql_w)

    def delete(self):
        query = self._delete()
        self.delete_uploaded_files()
        self._db['_lastsql'] = query
        self._db._execute(query)
        try:
            return self._db._cursor.rowcount
        except:
            return None

    def _update(self, **update_fields):
        tablenames = self._tables
        if len(tablenames) != 1:
            raise SyntaxError, 'SQLSet: unable to determine what to do'
        sql_t = tablenames[0]
        (table, dbname) = (self._db[sql_t], self._db._dbname)
        update_fields.update(dict([(field, table[field].update)
                             for field in table.fields if not field
                              in update_fields and table[field].update
                              != None]))
        sql_v = 'SET ' + ', '.join(['%s=%s' % (field,
                                   sql_represent(value,
                                   table[field].type, dbname))
                                   for (field, value) in
                                   update_fields.items()])
        if self.sql_w:
            sql_w = ' WHERE ' + self.sql_w
        else:
            sql_w = ''
        return 'UPDATE %s %s%s;' % (sql_t, sql_v, sql_w)

    def update(self, **update_fields):
        query = self._update(**update_fields)
        self.delete_uploaded_files(update_fields)
        self._db['_lastsql'] = query
        self._db._execute(query)
        try:
            return self._db._cursor.rowcount
        except:
            return None

    def delete_uploaded_files(self, upload_fields=None):
        table = self._db[self._tables[0]]

        # ## mind uploadfield==True means file is not in DB

        if upload_fields:
            fields = upload_fields.keys()
        else:
            fields = table.fields
        fields = [f for f in fields if table[f].type == 'upload'
                   and table[f].uploadfield == True
                   and table[f].autodelete]
        if not fields:
            return
        for record in self.select(*[table[f] for f in fields]):
            for fieldname in fields:
                oldname = record.get(fieldname, None)
                if not oldname:
                    continue
                if upload_fields and oldname == upload_fields[fieldname]:
                    continue
                oldpath = os.path.join(self._db._folder, '..', 
                                       'uploads', oldname)
                if os.path.exists(oldpath):
                    os.unlink(oldpath)

def update_record(t, s, a):
    s.update(**a)
    for (key, value) in a.items():
        t[str(key)] = value


class SQLRows(object):

    """
    A wrapper for the retun value of a select. It basically represents a table.
    It has an iterator and each row is represented as a dictionary.
    """

    # ## this class still needs some work to care for ID/OID

    def __init__(
        self,
        db,
        response,
        *colnames
        ):
        self._db = db
        self.colnames = colnames
        self.response = response
        self.hooks = True
        self.compact = True

    def __nonzero__(self):
        if len(self.response):
            return 1
        return 0

    def __len__(self):
        return len(self.response)

    def __getitem__(self, i):
        if i >= len(self.response) or i < 0:
            raise SyntaxError, 'SQLRows: no such row'
        if len(self.response[0]) != len(self.colnames):
            raise SyntaxError, 'SQLRows: internal error'
        row = SQLStorage()
        for j in xrange(len(self.colnames)):
            value = self.response[i][j]
            if not table_field.match(self.colnames[j]):
                if not '_extra' in row:
                    row['_extra'] = SQLStorage()
                row['_extra'][self.colnames[j]] = value
                continue
            (tablename, fieldname) = self.colnames[j].split('.')
            table = self._db[tablename]
            field = table[fieldname]
            if not tablename in row:
                row[tablename] = SQLStorage()
            if field.type[:9] == 'reference':
                referee = field.type[10:].strip()
                rid = value
                row[tablename][fieldname] = rid
            elif field.type == 'blob' and value != None:
                row[tablename][fieldname] = base64.b64decode(str(value))
            elif field.type == 'boolean' and value != None:
                if value == True or value == 'T' or value == 't':
                    row[tablename][fieldname] = True
                else:
                    row[tablename][fieldname] = False
            elif field.type == 'date' and value != None\
                 and (not isinstance(value, datetime.date)\
                      or isinstance(value, datetime.datetime)):
                (y, m, d) = [int(x) for x in
                             str(value)[:10].strip().split('-')]
                row[tablename][fieldname] = datetime.date(y, m, d)
            elif field.type == 'time' and value != None\
                 and not isinstance(value, datetime.time):
                time_items = [int(x) for x in
                              str(value)[:8].strip().split(':')[:3]]
                if len(time_items) == 3:
                    (h, mi, s) = time_items
                else:
                    (h, mi, s) = time_items + [0]
                row[tablename][fieldname] = datetime.time(h, mi, s)
            elif field.type == 'datetime' and value != None\
                 and not isinstance(value, datetime.datetime):
                (y, m, d) = [int(x) for x in
                             str(value)[:10].strip().split('-')]
                time_items = [int(x) for x in
                              str(value)[11:19].strip().split(':')[:3]]
                if len(time_items) == 3:
                    (h, mi, s) = time_items
                else:
                    (h, mi, s) = time_items + [0]
                row[tablename][fieldname] = datetime.datetime(y, m, d, h, mi, s)
            elif isinstance(field.type,SQLCustomType) and value != None:
                row[tablename][fieldname] = field.type.decoder(value)
            else:
                row[tablename][fieldname] = value
            if fieldname == 'id' and self.hooks:
                id = row[tablename].id
                row[tablename].update_record = lambda t = row[tablename], \
                    s = self._db(table.id == id), **a: update_record(t, s, a)
                for (referee_table, referee_name) in \
                    table._referenced_by:
                    s = self._db[referee_table][referee_name]
                    row[tablename][referee_table] = SQLSet(self._db, s == id)
        keys = row.keys()
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[row.keys()[0]]
        return row

    def as_list(self,
                compact=True,
                storage_to_dict=True,
                datetime_to_str=True):
        (compact, self.compact) = (self.compact, compact)
        (hooks, self.hooks) = (self.hooks, False)
        def dictit(d):
            if storage_to_dict:
                d = dict(d)
            if datetime_to_str:
                for k in d:
                    v = d[k]
                    if isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
                        d[k] = v.isoformat().replace('T',' ')[:19]
            return d
        items = [dictit(item) for item in self]
        (self.hooks, self.compact) =  (hooks, compact)
        return items

    def __iter__(self):
        """
        iterator over records
        """

        for i in xrange(len(self)):
            yield self[i]

    def export_to_csv_file(self, ofile, null='<NULL>'):
        writer = csv.writer(ofile)
        writer.writerow(self.colnames)

        def none_exception(value):
            if isinstance(value, unicode):
                return value.encode('utf8')
            if hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            if value == None:
                return null
            return value

        for record in self:
            row = []
            for col in self.colnames:
                if not table_field.match(col):
                    row.append(record._extra[col])
                else:
                    (t, f) = col.split('.')
                    if isinstance(record.get(t, None), SQLStorage):
                        row.append(none_exception(record[t][f]))
                    else:
                        row.append(none_exception(record[f]))
            writer.writerow(row)

    def __str__(self):
        """
        serializes the table into a csv file
        """

        s = cStringIO.StringIO()
        self.export_to_csv_file(s)
        return s.getvalue()

    def xml(self):
        """
        serializes the table using sqlhtml.SQLTABLE (if present)
        """

        import sqlhtml
        return sqlhtml.SQLTABLE(self).xml()

    def json(self, mode='object'):
        """
        serializes the table to a JSON list of objects
        """

        mode = mode.lower()
        if not mode in ['object', 'array']:
            raise SyntaxError, 'Invalid JSON serialization mode.'

        def inner_loop(record, col):
            (t, f) = col.split('.')
            res = None
            if not table_field.match(col):
                res = record._extra[col]
            else:
                if isinstance(record.get(t, None), SQLStorage):
                    res = record[t][f]
                else:
                    res = record[f]
            if mode == 'object':
                return (f, res)
            else:
                return res

        if mode == 'object':
            items = [dict([inner_loop(record, col) for col in
                     self.colnames]) for record in self]
        else:
            items = [[inner_loop(record, col) for col in self.colnames]
                     for record in self]

        return json(items)


def test_all():
    """    

    Create a table with all possible field types
    'sqlite://test.db'
    'mysql://root:none@localhost/test'
    'postgres://mdipierro:none@localhost/test'
    'mssql://web2py:none@A64X2/web2py_test'
    'firebird://user:password@server:3050/database'
    'db2://DSN=dsn;UID=user;PWD=pass'

    >>> if len(sys.argv)<2: db=SQLDB(\"sqlite://test.db\")
    >>> if len(sys.argv)>1: db=SQLDB(sys.argv[1])
    >>> tmp=db.define_table('users',\
              SQLField('stringf','string',length=32,required=True),\
              SQLField('booleanf','boolean',default=False),\
              SQLField('passwordf','password',notnull=True),\
              SQLField('blobf','blob'),\
              SQLField('uploadf','upload'),\
              SQLField('integerf','integer',unique=True),\
              SQLField('doublef','double',unique=True,notnull=True),\
              SQLField('datef','date',default=datetime.date.today()),\
              SQLField('timef','time'),\
              SQLField('datetimef','datetime'),\
              migrate='test_user.table')

   Insert a field

    >>> db.users.insert(stringf='a',booleanf=True,passwordf='p',blobf='0A',\
                       uploadf=None, integerf=5,doublef=3.14,\
                       datef=datetime.date(2001,1,1),\
                       timef=datetime.time(12,30,15),\
                       datetimef=datetime.datetime(2002,2,2,12,30,15))
    1

    Drop the table   

    >>> db.users.drop()

    Examples of insert, select, update, delete

    >>> tmp=db.define_table('person',\
              SQLField('name'),\
              SQLField('birth','date'),\
              migrate='test_person.table')
    >>> person_id=db.person.insert(name=\"Marco\",birth='2005-06-22')
    >>> person_id=db.person.insert(name=\"Massimo\",birth='1971-12-21')
    >>> len(db().select(db.person.ALL))
    2
    >>> me=db(db.person.id==person_id).select()[0] # test select
    >>> me.name
    'Massimo'
    >>> db(db.person.name=='Massimo').update(name='massimo') # test update
    1
    >>> db(db.person.name=='Marco').delete() # test delete
    1

    Update a single record

    >>> me.update_record(name=\"Max\")
    >>> me.name
    'Max'

    Examples of complex search conditions

    >>> len(db((db.person.name=='Max')&(db.person.birth<'2003-01-01')).select())
    1
    >>> len(db((db.person.name=='Max')&(db.person.birth<datetime.date(2003,01,01))).select())
    1
    >>> len(db((db.person.name=='Max')|(db.person.birth<'2003-01-01')).select())
    1
    >>> me=db(db.person.id==person_id).select(db.person.name)[0] 
    >>> me.name
    'Max'
  
    Examples of search conditions using extract from date/datetime/time      

    >>> len(db(db.person.birth.month()==12).select())
    1
    >>> len(db(db.person.birth.year()>1900).select())
    1

    Example of usage of NULL

    >>> len(db(db.person.birth==None).select()) ### test NULL
    0
    >>> len(db(db.person.birth!=None).select()) ### test NULL
    1

    Examples of search consitions using lower, upper, and like

    >>> len(db(db.person.name.upper()=='MAX').select())
    1
    >>> len(db(db.person.name.like('%ax')).select())
    1
    >>> len(db(db.person.name.upper().like('%AX')).select())
    1
    >>> len(db(~db.person.name.upper().like('%AX')).select())
    0

    orderby, groupby and limitby 

    >>> people=db().select(db.person.name,orderby=db.person.name)
    >>> order=db.person.name|~db.person.birth
    >>> people=db().select(db.person.name,orderby=order)
    
    >>> people=db().select(db.person.name,orderby=db.person.name,groupby=db.person.name)
    
    >>> people=db().select(db.person.name,orderby=order,limitby=(0,100))

    Example of one 2 many relation

    >>> tmp=db.define_table('dog',\
               SQLField('name'),\
               SQLField('birth','date'),\
               SQLField('owner',db.person),\
               migrate='test_dog.table')
    >>> db.dog.insert(name='Snoopy',birth=None,owner=person_id)
    1

    A simple JOIN

    >>> len(db(db.dog.owner==db.person.id).select())
    1

    >>> len(db().select(db.person.ALL,db.dog.name,left=db.dog.on(db.dog.owner==db.person.id)))
    1

    Drop tables

    >>> db.dog.drop()
    >>> db.person.drop()

    Example of many 2 many relation and SQLSet
 
    >>> tmp=db.define_table('author',SQLField('name'),\
                            migrate='test_author.table')
    >>> tmp=db.define_table('paper',SQLField('title'),\
                            migrate='test_paper.table')
    >>> tmp=db.define_table('authorship',\
            SQLField('author_id',db.author),\
            SQLField('paper_id',db.paper),\
            migrate='test_authorship.table')
    >>> aid=db.author.insert(name='Massimo')
    >>> pid=db.paper.insert(title='QCD')
    >>> tmp=db.authorship.insert(author_id=aid,paper_id=pid)

    Define a SQLSet

    >>> authored_papers=db((db.author.id==db.authorship.author_id)&(db.paper.id==db.authorship.paper_id))
    >>> rows=authored_papers.select(db.author.name,db.paper.title)
    >>> for row in rows: print row.author.name, row.paper.title
    Massimo QCD

    Example of search condition using  belongs

    >>> set=(1,2,3)
    >>> rows=db(db.paper.id.belongs(set)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of search condition using nested select

    >>> nested_select=db()._select(db.authorship.paper_id)
    >>> rows=db(db.paper.id.belongs(nested_select)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of expressions

    >>> mynumber=db.define_table('mynumber',SQLField('x','integer'))
    >>> db(mynumber.id>0).delete()
    0
    >>> for i in range(10): tmp=mynumber.insert(x=i)
    >>> db(mynumber.id>0).select(mynumber.x.sum())[0]._extra[mynumber.x.sum()]
    45
    >>> db(mynumber.x+2==5).select(mynumber.x+2)[0]._extra[mynumber.x+2]
    5

    Output in csv

    >>> print str(authored_papers.select(db.author.name,db.paper.title)).strip()
    author.name,paper.title\r
    Massimo,QCD

    Delete all leftover tables

    # >>> SQLDB.distributed_transaction_commit(db)

    >>> db.mynumber.drop()
    >>> db.authorship.drop()
    >>> db.author.drop()
    >>> db.paper.drop()
    """


if __name__ == '__main__':
    import doctest
    doctest.testmod()
