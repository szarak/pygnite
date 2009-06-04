#!/usr/bin/python
# -*- coding: utf-8 -*-

from ignite.sql import *
from ignite.validators import *

db = database(engine='sqlite3', db='app/db/database.db')

from db import *
