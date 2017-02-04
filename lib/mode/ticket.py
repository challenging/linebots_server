#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lib.common.utils import MODE_TICKET
from lib.common.mode import Mode

class TicketoMode(Mode):
    def is_process(self, mode):
        return self.mode.lower() == mode.lower()

    def process(self, question, user_id=None, user_name=None):
        reply_txt = None

        return reply_txt

mode_ticket = TicketMode(MODE_TICKET)
