#!/usr/bin/python
# -*- coding: utf-8 -*-

from ignite import *

import model

@url('^/$', method='GET')
def index(request):
    return 'Hello world'

@url('^/hello/(?P<name>\w+)/?$')
def hello(request, *args, **kwargs):
    return 'Hello %s' % kwargs.get('name')

if __name__ == '__main__':
    ignite()
