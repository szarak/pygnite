#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import cgi

from utils import *
from template import *
from main import IGNITE_PATH

from httplib import responses

__all__ = ['routes', 'url', 'get', 'post', 'put', 'delete', 'Request', 'Response', 'redirect', '_404', '_500']

routes = Storage({ 'GET' : Storage(), 'POST' : Storage(), 'PUT' : Storage(), 'DELETE' : Storage() })

def url(regex, methods=['*'], content_type='text/html'):
    """
    Route decorator.

    example:
        >>> @url('^/$')
            def foo(request):
                pass
        
        will return foo function when address is /

    :param regex: Regexp for url path.
    :param methods: Lists of methods, if ['*'] match all. 
    :param content_type: Content Type of returned text. 

    """
    def wrap(f):
        if methods[0] == '*':
            _methods = routes.keys()
        else:
            _methods = methods

        for method in _methods:
            if method in routes:
                if not routes[method].has_key(regex):
                    route = { re.compile(regex) : (f, content_type) }
                    routes[method].update(route)
    return wrap

def get(regex, **kwds):
    """
    Shortcut for:

        >>> @url(regex, methods=['GET'])
    """
    def wrap(f):
        return url(regex, methods=['GET'], **kwds)(f)
    return wrap

def post(regex, **kwds):
    """
    Shortcut for:
        
        >>> @url(regex, methods=['POST'])
    """
    def wrap(f):
        return url(regex, methods=['POST'], **kwds)(f)
    return wrap

def put(regex, **kwds):
    """
    Shortcut for:
    
        >>> @url(regex, methods=['PUT'])
    """
    def wrap(f):
        return url(regex, methods=['PUT'], **kwds)(f)
    return wrap

def delete(regex, **kwds):
    """
    Shortcut for:
    
        >>> @url(regex, methods=['DELETE'])
    """
    def wrap(f):
        return url(regex, methods=['DELETE'], **kwds)(f)
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

    def __init__(self, body='', content_type='text/html', status=200):
        self.body = body
        self.content_type = content_type
        self.status = get_response_status(status)

    def __call__(self, env, start_response):
        self.headers['Content-type'] = self.content_type
        self.headers['Content-length'] = str(len(self.body))

        start_response(self.status, self.headers.items())
        return [ str(self.body) ]


def redirect(location, body='redirecting...', status=302, **kwds):
    """
    Redirect.

    :param location: Location. 
    :param body: Body.
    :param status: Status.
    """

    status = get_response_status(status)

    response = Response(body=body, status=status, **kwds)
    response.headers['Location'] = location

    return response

append_path(IGNITE_PATH + '/templates/')

def _500(body=''):
    """
    Return error 500.
    """
    return render('500.html', body=body)

def _404():
    """
    Return error 404. 
    """
    return render('404.html')


