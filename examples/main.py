#!/usr/bin/python
# -*- coding: utf-8 -*-

from ignite import *

import model

@url('^/$', method='GET')
def index(request):
    return 'Hello world'

@url('^/hello/([^/]*)/(?P<lastname>[^/]*)/?$')
def hello(request, *vars, **v):
    return 'Hello %s' % vars[0]

if __name__ == '__main__':
    ignite()
