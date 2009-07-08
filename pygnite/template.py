#!/usr/bin/python
# -*- coding: utf-8 -*-

# Jinja2 templates

from jinja2 import Environment 
from jinja2 import FileSystemLoader

env = Environment(loader=FileSystemLoader([]))

def append_path(paths):
    if isinstance(paths, str):
        paths = [paths]

    for path in paths:
        if not path in env.loader.searchpath:
            env.loader.searchpath.append(path)


def render(template_name, **context):
    from main import request

    template = env.get_template(template_name)
    return template.render(request=request, session=request.session, **context)
