#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import traceback

from werkzeug import run_simple
from beaker.middleware import SessionMiddleware

IGNITE_PATH = os.path.dirname(__file__)

from http import *
from storage import *
from sql import *
from html import *
from sqlhtml import *
from validators import *
from template import *


def create_app(env, start_response):
    global request

    request = Request(env)
    request.session = env['beaker.session']

    if request.session.has_key('flash'):
        del request.session['flash']
    else:
        request.session['flash'] = None

    _routes = routes[request.method]
    for route in _routes:
        match = route.match(request.path)
        if match is not None:
            unamed_vars = match.groups() or ()
            named_vars = match.groupdict() or {}

            (f, content_type) = _routes[route]
            try:
                controller = f(request, *unamed_vars, **named_vars)

                if isinstance(controller, basestring):
                    controller = Response(controller, content_type=content_type)

                request.session.save()
                return controller(env, start_response)

            except:
                t = traceback.format_exception(*sys.exc_info())
                return Response(_500(''.join(t)))(env, start_response)

    return Response(_404())(env, start_response)


def ignite(host='127.0.0.1', port=6060, session_key='mysession', session_secret='randomsecret'):
    app = SessionMiddleware(create_app, key=session_key, secret=session_secret)
    run_simple(host, port, app, use_reloader=True)


