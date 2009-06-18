#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
        name='Ignite',
        description='Ignite is simple web framework written in Python.',
        author='Kacper Krupa',
        author_email='pagenoare@gmail.com',
        url='http://pagenoare.net/ignite/',
        version='0.1.2',
        packages=['ignite'],
        license='GPLv2',
        install_requires=['werkzeug', 'beaker'],
)


