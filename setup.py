#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
        name='pygnite',
        description='Pygnite is simple web framework written in Python.',
        author='Kacper Krupa',
        author_email='pagenoare@gmail.com',
        url='http://pygnite.com',
        version='0.1.2',
        packages=['pygnite'],
        include_package_data = True,
        package_data={ 'pygnite' : ['templates/*.html'] },
        license='GPLv2',
        install_requires=['werkzeug', 'flup', 'beaker'],
)


