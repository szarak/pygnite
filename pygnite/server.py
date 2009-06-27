#!/usr/bin/python
# -*- coding: utf-8 -*-

SERVERS = ['dev', 'fcgi']

def dev(app, host='127.0.0.1', port='6060', **kwds):
    """
    Lunch dev server.

    :param app: Application.
    :param host: Hostname.
    :param port: Port.
    :param auto_reload: If True check files changes and reload server.
    """

    from werkzeug import run_simple
    run_simple(host, port, app, use_reloader=kwds.get('auto_reload', True))

def fcgi(app, host=None, port=None, **kwds):
    """
    Run fcgi server.

    :param app: Application.
    :param host: Hostname.
    :param port: Port.
    """

    from flup.server.fcgi import WSGIServer as fcgi
    addr = (host, port) if port else None
    fcgi(app, bindAddress=addr).run()

# TODO:
def scgi():
    pass

def gae():
    pass
