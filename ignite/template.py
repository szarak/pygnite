#!/usr/bin/python
# -*- coding: utf-8 -*-

# Jinja2 templates

from jinja2 import Environment 
from jinja2 import FileSystemLoader

templates_path = []

def append_path(path):
    global env

    if type(path) == str:
        path = [path]

    for p in path:
        if not p in templates_path:
            templates_path.append(p)

    env = Environment(loader=FileSystemLoader(templates_path))

def render(template_name, **context):
    from main import request

    template = env.get_template(template_name)
    return template.render(session=request.session, **context)
