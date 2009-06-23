#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import traceback

from beaker.middleware import SessionMiddleware

IGNITE_PATH = os.path.dirname(__file__)

from http import *
from utils import *
from sql import *
from html import *
from sqlhtml import *
from validators import *
from template import *


def create_app(env, start_response):
    global request

    request = Request(env)
    request.session = env['beaker.session']
    request.flash = request.session.get('flash', None)
    request.session['flash'] = None

    _routes = routes[request.method]
    for route in _routes:
        match = route.match(request.path)
        if match is not None:
            vars = match.groupdict() or {}
            if not vars and match.groups():
                vars['unnamed'] = match.groups()

            (f, content_type) = _routes[route]
            try:
                controller = f(request, **vars)

                if isinstance(controller, basestring):
                    controller = Response(controller, content_type=content_type)

                request.session.save()
                return controller(env, start_response)

            except:
                t = traceback.format_exception(*sys.exc_info())
                return Response(_500(''.join(t)))(env, start_response)

    return Response(_404())(env, start_response)


def ignite(**conf):
    ## Conf to var assignment
    # Serving conf
    mode = conf.get('mode', 'dev')
    host = conf.get('host', '127.0.0.1')
    port = conf.get('port', 6060)
    # templates path. ofc you can add it manually by template.append_path
    templates_path = conf.get('templates_path', os.path.join(sys.path[0], 'templates'))
    append_path(templates_path)
    # Session config
    session_key = conf.get('session_key', 'mysession')
    session_secret = conf.get('session_secret', 'randomsecret')

    if not mode in ('dev', 'fcgi', 'scgi', 'gae'):
        # if mode not supported, choose dev
        mode = 'dev'

    ## Session middleware:
    app = SessionMiddleware(create_app, key=session_key, secret=session_secret)

    if mode == 'dev':
        # run dev server
        from werkzeug import run_simple
        run_simple(host, port, app, use_reloader=True)
    elif mode == 'fcgi':
        # run fcgi
        from flup.server.fcgi import WSGIServer as fcgi
        addr = (host, port) if port else None
        fcgi(app, bindAddress=addr).run()
    elif mode == 'scgi':
        # run scgi
        pass
    elif mode == 'gae':
        # run gae
        pass


