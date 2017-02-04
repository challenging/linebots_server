#!/usr/bin/env python

from lib.db.mode import db_mode

class Mode(object):
    def __init__(self, mode):
        self._mode = mode

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        self._mode = mode

    def conversion(self, question, user_id, user_name):
        raise NotImplementedError
