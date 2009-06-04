#!/usr/bin/python
# -*- coding: utf-8 -*-

from werkzeug import run_simple
from werkzeug import Request
from werkzeug import Response

from http import *
from storage import Storage
from sql import *
from html import *
from validators import *

from beaker.middleware import SessionMiddleware

def create_app(env, start_response):
    request = Request(env)
    request.session = env['beaker.session']

    request.vars = Storage()
    # Add GET vars to request.vars
    for key, value in request.args.iteritems():
        if type(value) == list and len(value) == 1:
            value = value[0]

        request.vars[key] = value

    # Add POST vars to request.vars
    for key, value in request.form.iteritems():
        if type(value) == list and len(value) == 1:
            value = value[0]

        request.vars[key] = value

    for route in routes:
        match = route.match(request.path)
        if match is not None:
            unamed_vars = match.groups() or ()
            named_vars = match.groupdict() or {}

            f = routes[route]
            controller = f(request, *unamed_vars, **named_vars)
            if isinstance(controller, basestring):
                controller = Response(controller, mimetype='text/html')

            return controller(env, start_response)

    return Response(not_found(), mimetype='text/html')(env, start_response)


def ignite(host='127.0.0.1', port=6060):
    app = SessionMiddleware(create_app, key='mysession', secret='randomsecret')
    run_simple(host, port, app, use_reloader=True)


