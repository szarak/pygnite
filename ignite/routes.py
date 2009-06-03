#!/usr/bin/python
# -*- coding: utf-8 -*-
import re

routes = dict(GET=dict(), POST=dict())

def url(addr, method='GET'):
    def wrap(f):
        if not routes[method].has_key(addr):
            route = { re.compile(addr) : f }
            routes[method].update(route)
    return wrap
