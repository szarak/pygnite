#!/usr/bin/python
# -*- coding: utf-8 -*-

from ignite import *

from app.models import *

@get('^/$')
def index(request):
    return render('index.html')

@url('^/register/?$', methods=['GET', 'POST'])
def register(request):
    form = SQLFORM(db.user)

    if form.accepts(request.vars):
        db.commit()
        request.session['flash'] = 'You\'ve been registred. '
        return redirect('/')

    return render('form.html', form=form)

@url('^/login/?$', methods=['GET', 'POST'])
def login(request):
    db.user.login.requires = IS_NOT_EMPTY()
    form = SQLFORM(db.user, fields=['login', 'password'])

    if FORM.accepts(form, request.vars):
        query = db((db.user.login == form.vars.login) &
                   (db.user.password == form.vars.password))

        if query.count() == 1:
            user = query.select()[0]
            request.session['user'] = Storage(login=user.login, id=user.id, 
                                            email=user.email)
            request.session['flash'] = 'You\'ve been logged in'
            return redirect('/')
        else:
            request.session['flash'] = 'User not found'
            return redirect('/login')

    return render('form.html', form=form)

@get('^/logout/?')
def logout(request):
    if request.session.has_key('user'):
        del request.session['user']

    request.session['flash'] = 'Bye, bye'
    return redirect('/')


