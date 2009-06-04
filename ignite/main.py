#!/usr/bin/python
# -*- coding: utf-8 -*-

import traceback

from werkzeug import run_simple

from http import *
from storage import *
from sql import *
from html import *
from validators import *
from template import *

from beaker.middleware import SessionMiddleware

def create_app(env, start_response):
    request = Request(env)
    request.session = env['beaker.session']

    for route in routes:
        match = route.match(request.path)
        if match is not None:
            unamed_vars = match.groups() or ()
            named_vars = match.groupdict() or {}

            f = routes[route]
            controller = f(request, *unamed_vars, **named_vars)

            if isinstance(controller, basestring):
                controller = Response(controller)

            return controller(env, start_response)

    return Response(_404())(env, start_response)


def ignite(host='127.0.0.1', port=6060):
    app = SessionMiddleware(create_app, key='mysession', secret='randomsecret')
    run_simple(host, port, app, use_reloader=True)
