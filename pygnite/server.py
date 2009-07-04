#!/usr/bin/python
# -*- coding: utf-8 -*-

SERVERS = ['dev', 'fcgi', 'scgi', 'gae']

def dev(app, host='127.0.0.1', port='6060', **kwds):
    """
    Lunch dev server.

    :param app: Application.
    :param host: Hostname.
    :param port: Port.
    :param auto_reload: If True check files changes and reload server.
    """

    from werkzeug import run_simple
    return run_simple(host, port, app, use_reloader=kwds.get('auto_reload', True))

def fcgi(app, host=None, port=None, **kwds):
    """
    Run fcgi server.

    :param app: Application.
    :param host: Hostname.
    :param port: Port.
    """

    from flup.server.fcgi import WSGIServer as fcgi
    addr = (host, port) if port else None
    return fcgi(app, bindAddress=addr).run()

def scgi(app, host=None, port=None, **kwds):
    """
    Run scgi server.

    :param app: Application.
    :param host: Hostname.
    :param port: Port.
    """

    from flup.server.scgi_fork import WSGIServer as scgi
    addr = (host, port) if port else None
    return scgi(application=app, bindAddress=addr).run()

def gae(app, host, port, **kwds):
    from google.appengine.ext.webapp.util import run_wsgi_app

    return run_wsgi_app(app)

