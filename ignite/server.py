#!/usr/bin/python
# -*- coding: utf-8 -*-

from paste import httpserver
from paste.exceptions.errormiddleware import ErrorMiddleware

from webob import Request
from webob import Response

__all__ = ['server']

def foo(request):
    return 'chuj'

def server(env, start_response):
    request = Request(env)
    controller = foo(request)
    return Response(body=controller)(env, start_response)

app = ErrorMiddleware(server, debug=True)
httpserver.serve(app, host='127.0.0.1', port=6060)
