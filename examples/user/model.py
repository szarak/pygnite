#!/usr/bin/python
# -*- coding: utf-8 -*-

from pygnite import *

db = database(engine='sqlite3', db='db/database.db')

db.define_table('user',
        db.Field('login', 'string'),
        db.Field('password', 'password'),
        db.Field('email', 'string'),
)

db.user.login.requires = [ IS_NOT_EMPTY(), IS_NOT_IN_DB(db, 'user.login') ]
db.user.password.requires = [ IS_NOT_EMPTY(), CRYPT() ]
db.user.email.requires = IS_EMAIL()
