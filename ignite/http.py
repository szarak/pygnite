#!/usr/bin/python
# -*- coding: utf-8 -*-
import re

from template import *

routes = dict()

def url(addr):
    def wrap(f):
        if not routes.has_key(addr):
            route = { re.compile(addr) : f }
            routes.update(route)
    return wrap

def not_found():
    setup_templates('/home/pagenoare/Projects/ignite/ignite/templates/')
    return render('404.html')


