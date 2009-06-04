#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import cgi

from urlparse import *

from storage import Storage
from template import *

from httplib import responses

__all__ = ['routes', 'url', 'Request', 'Response', 'redirect', '_404']

routes = dict()

def url(addr):
    def wrap(f):
        if not routes.has_key(addr):
            route = { re.compile(addr) : f }
            routes.update(route)
    return wrap

def get_response_status(status):
    return "%s %s" % (status, responses.get(status))

class Request(Storage):
    """Ignite request object"""

    def __init__(self, env):
        for meta in env:
            if meta == 'PATH_INFO':
                self.path = env[meta] or '/'
            else:
                name = meta.replace('.', '_')
                self[name] = env[meta]

        self.vars = Storage()
        # GET vars:
        self.vars.update(self.parse_get())
        # POST vars:
        self.vars.update(self.parse_post())

    def parse_get(self):
        query = self.QUERY_STRING
        vars = Storage()
        if query:
            if '&' in query:
                for var in query.split('&'):
                    (key, value) = var.split('=', 1)
                    vars[key] = value
            else:
                (key, value) = query.split('=', 1)
                vars[key] = value

        del self['QUERY_STRING']

        return vars

    def parse_post(self):
        vars = Storage()
        fs = cgi.FieldStorage(fp=self['wsgi_input'], environ=self)
        for field in fs.list:
            if field is not None:
                name = field.name
                if field.filename:
                    value = field
                else:
                    value = field.value
                if vars.has_key(name):
                    vars[name] = [vars[name]]
                    vars[name].append(value)
                else:
                    vars[name] = value

        del self['wsgi_input']

        return vars

class Response(object):
    """Ignite response object"""

    headers = {}

    def __init__(self, body='', mimetype='text/html', status=200):
        self.body = body
        self.mimetype = mimetype
        self.status = get_response_status(status)

    def __call__(self, env, start_response):
        self.headers['Content-type'] = self.mimetype
        self.headers['Content-length'] = len(self.body)

        start_response(self.status, self.headers.items())
        return [ str(self.body) ]


def redirect(location, body='redirecting...', status=302, **kwds):
    status = get_response_status(status)

    response = Response(body=body, status=status, **kwds)
    response.headers['Location'] = location

    return response

def _404():
    setup_templates('/home/pagenoare/Projects/ignite/ignite/templates/')
    return render('404.html')


