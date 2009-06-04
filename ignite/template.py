#!/usr/bin/python
# -*- coding: utf-8 -*-

# Jinja2 templates

from jinja2 import Environment, FileSystemLoader

def setup_templates(path):
    global env
    if type(path) == str:
        path = [path]

    env = Environment(loader=FileSystemLoader(path))

def render(template_name, **context):
    global env
    template = env.get_template(template_name)
    return template.render(**context)
