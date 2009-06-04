#!/usr/bin/python
# -*- coding: utf-8 -*-

from ignite import *

setup_templates('/home/pagenoare/Projects/ignite/templates/')

@get('^/$')
def index(request):
    return redirect('/post/')

@url('^/post/$', methods=['GET', 'POST'])
def post(request):
    form = FORM(
            INPUT(_name='name', requires=IS_NOT_EMPTY()),
            INPUT(_type='submit'),
            )

    if form.accepts(request.vars):
        return 'Hello %s' % request.vars.name

    return render('post.html', form=form)

if __name__ == '__main__':
    ignite()
