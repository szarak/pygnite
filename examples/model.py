#!/usr/bin/python
# -*- coding: utf-8 -*-

from ignite.sql import database

db = database(engine='sqlite3', db='db/database.db')

db.define_table('test', db.Field('title'))
