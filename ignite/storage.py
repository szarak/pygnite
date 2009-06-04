#!/usr/bin/python
# -*- coding: utf-8 -*-

__all__ = ['Storage']

class Storage(dict):

    def __getattr__(self, value):
        return self.get(value, None)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
