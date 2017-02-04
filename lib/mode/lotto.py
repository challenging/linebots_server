#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lib.db import lotto
from lib.common.utils import MODE_LOTTO
from lib.common.mode import Mode

class LottoMode(Mode):
    MONEY = 35

    def is_process(self, mode):
        return self.mode.lower() == mode.lower()

    def process(self, question, user_id=None, user_name=None):
        if question.isdigit():
            fee = int(question)
            if fee > 0 and fee < self.MONEY:
                 lotto.db_lotto.ask(user_id, user_name, fee)

                 count = 0
                 users = set()
                 for row in db_lotto.query():
                     user_id, user_name, creation_datetime, money = row
                     if money > 0 and money < self.MONEY:
                        if user_id not in users and fee == money:
                            count += 1

                        users.add(user_id)

                 reply_txt = "您現今競標的金額是 {} 元(有{}人與您出價相同)".format(fee, count-1)
            elif fee >= self.MONEY:
                 reply_txt = "金額需要小於{}元，不然你請大家喝飲料好了，謝謝！".format(self.MONEY)
        else:
            reply_txt = "請輸入正整數型態（不要耍笨，輸入這鬼東西[{}]）".format(question)

        return reply_txt

    def is_open(self, question):
        return question == "game start"

    def is_over(self, question):
        return question == "game over"

    def is_delete(self, question):
        return question == "delete game"

mode_lotto = LottoMode(MODE_LOTTO)
lotto_opened = True
