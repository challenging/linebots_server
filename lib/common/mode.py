#!/usr/bin/env python

from lib.db.mode import db_mode

class Mode(object):
    def __init__(self, mode):
        self._mode = mode

        self.init()

    def init(self):
        pass

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        self._mode = mode

    def is_process(self, mode, question):
        raise mode.lower() == self.mode.lower()

    def conversion(self, question, user_id, user_name):
        raise NotImplementedError
