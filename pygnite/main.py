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
from server import *

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
            params = Storage()
            params.update(match.groupdict())
            params['all'] = match.groups()

            (f, content_type) = _routes[route]
            try:
                try:
                    controller = f(request, params)
                except TypeError:
                    controller = f(request)

                if isinstance(controller, basestring):
                    controller = Response(controller, content_type=content_type)

                request.session.save()
                return controller(env, start_response)

            except:
                t = traceback.format_exception(*sys.exc_info())
                return _500(''.join(t))(env, start_response)

    return _404()(env, start_response)


def pygnite(**conf):
    """
    Main pygnite function which lunches supported server.

    :param mode: Server mode (see server module for supported)
    :param host: Hostname.
    :param port: Port.
    :param server_conf: Extra server configuration.
    :param templates_path: Path to templates.
    :param session_key: Session key.
    :param session_secret: Session secret.
    """
    ## Conf to var assignment
    # Serving conf
    mode = conf.get('mode', 'dev')
    host = conf.get('host', '127.0.0.1')
    port = conf.get('port', 6060)
    server_conf = conf.get('server_conf', {})
    # templates path. ofc you can add it manually by template.append_path
    templates_path = conf.get('templates_path', os.path.join(sys.path[0], 'templates'))
    append_path(templates_path)
    # Session config
    session_key = conf.get('session_key', 'mysession')
    session_secret = conf.get('session_secret', 'randomsecret')

    if not mode in SERVERS:
        # if mode not supported, choose dev
        mode = 'dev'

    ## Session middleware:
    app = SessionMiddleware(create_app, key=session_key, secret=session_secret)

    if mode == 'dev' and not server_conf.has_key('auto_reload'):
        server_conf['auto_reload'] = True

    eval('%s(app, host, port, **server_conf)' % mode)

