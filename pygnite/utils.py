#!/usr/bin/python
# -*- coding: utf-8 -*-

__all__ = ['Storage', 'hash']

import hashlib

class Storage(dict):
    """
    Storage is a dict-like object, where items can be accessed like attributtes.

    ::

        d = Storage()
        d.foo = 'bar' # it's d['foo'] = 'bar'

    """

    def __getattr__(self, value):
        return self.get(value, None)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]


def hash(value, digest_alg='md5'):
    """
    Return hashed string by ``digest_alg``.
    """

    h = hashlib.new(digest_alg)
    h.update(value)
    return h.hexdigest()

