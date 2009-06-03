#!/usr/bin/python
# -*- coding: utf-8 -*-

from werkzeug import run_simple
from werkzeug import Request
from werkzeug import Response
from werkzeug.exceptions import NotFound

from routes import *

def not_found():
    return "<h1>404</h1>"

def create_app(env, start_response):
    request = Request(env)
    _routes = routes.get(request.method, 'GET')

    for route in _routes:
        match = route.match(request.path)
        if match is not None:
            unamed_vars = match.groups() or {}
            named_vars = match.groupdict() or {}

            f = _routes[route]
            controller = f(request, *unamed_vars, **named_vars)
            if isinstance(controller, basestring):
                controller = Response(controller)

            return controller(env, start_response)

    return Response(not_found())(env, start_response)


def ignite(host='127.0.0.1', port=6060):
    run_simple(host, port, create_app, use_reloader=True)


