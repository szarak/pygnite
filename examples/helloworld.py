#!/usr/bin/python
# -*- coding: utf-8 -*-

from pygnite import *

@get('/')
def index(request):
    return 'Hello world'


if __name__ == '__main__': pygnite()
