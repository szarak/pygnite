#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import cgi

from storage import *
from template import *
from main import IGNITE_PATH

from httplib import responses

__all__ = ['routes', 'url', 'get', 'post', 'put', 'delete', 'Request', 'Response', 'redirect', '_404', '_500']

routes = Storage({ 'GET' : Storage(), 'POST' : Storage(), 'PUT' : Storage(), 'DELETE' : Storage() })

def url(addr, methods=['GET'], response_type='text/html'):
    def wrap(f):
        for method in methods:
            if method in routes:
                if not routes[method].has_key(addr):
                    route = { re.compile(addr) : (f, response_type) }
                    routes[method].update(route)
    return wrap

def get(addr, **kwds):
    def wrap(f):
        return url(addr, methods=['GET'], **kwds)(f)
    return wrap

def post(addr, **kwds):
    def wrap(f):
        return url(addr, methods=['POST'], **kwds)(f)
    return wrap

def put(addr, **kwds):
    def wrap(f):
        return url(addr, methods=['PUT'], **kwds)(f)
    return wrap

def delete(addr, **kwds):
    def wrap(f):
        return url(addr, methods=['DELETE'], **kwds)(f)
    return wrap

def get_response_status(status):
    return "%s %s" % (status, responses.get(status))

class Request(Storage):
    """Ignite request object"""

    def __init__(self, env):
        self.path = env['PATH_INFO'] or '/'
        self.method = env['REQUEST_METHOD']

        self.update(env)

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
        fs = cgi.FieldStorage(fp=self['wsgi.input'], environ=self)
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

        del self['wsgi.input']

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

append_path(IGNITE_PATH + '/templates/')

def _500(body=''):
    return render('500.html', body=body)

def _404():
    return render('404.html')


