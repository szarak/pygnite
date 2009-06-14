#!/usr/bin/python
# -*- coding: utf-8 -*-

__all__ = ['Storage', 'hash', 'Session']

import hashlib
from beaker.session import SessionObject


class Storage(dict):

    def __getattr__(self, value):
        return self.get(value, None)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]


def hash(value, digest_alg='md5'):
    h = hashlib.new(digest_alg)
    h.update(value)
    return h.hexdigest()

class Session(SessionObject, Storage):
    pass
