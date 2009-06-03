#!/usr/bin/python
# -*- coding: utf-8 -*-

from paste import httpserver

from webob import Request
from webob import Response
from webob import exc

from routes import *

def create_app(env, start_response):
    request = Request(env)
    _routes = routes.get(request.method, 'GET')

    for route in _routes:
        match = route.match(request.path_info)
        if match is not None:
            unamed_vars = match.groups()
            named_vars = match.groupdict()

            f = _routes[route]
            controller = f(request, *unamed_vars, **named_vars)
            if isinstance(controller, basestring):
                controller = Response(body=controller)

            return controller(env, start_response)

    return exc.HTTPNotFound()(env, start_response)

def ignite(host='127.0.0.1', port=6060):
    httpserver.serve(create_app, host=host, port=port)


