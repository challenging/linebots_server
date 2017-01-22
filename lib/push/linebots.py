#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random

from linebot import LineBotApi

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

from server.push import db
from server.db import mode, lotto
from lib.utils import MONEY
#from server.bot import weather, lucky, bus

# get channel_secret and channel_access_token from your environment variable
channel_secret = "b7cbe59211c0d67e6b37f7f2ccf43fdc"
channel_access_token = "Toi86OSQGdP6Ss2YVBGTl7eJ91h0z9dYPLVrzjkCQ0TWhd5O7UyTRIGhLYOAhDJBZxxqzavvdL7kAfPdxenlogkah8sucT96Iz7tT6MmMRQ5x5xjek5nzOn8cECZNS1kvCz/8LlrmIKZlxQdP2UgkwdB04t89/1O/w1cDnyilFU="

line_bot_api = LineBotApi(channel_access_token)

def push(user_id, reply_txt):
    #line_bot_api.push_message(user_id, TextSendMessage(text=reply_txt))
    print user_id, reply_txt

def lotto_results():
    from server.db import mode

    results = {}

    users = set()
    for row in lotto.db_lotto.query():
        user_id, user_name, creation_datetime, money = row
        if money > 0 and money < MONEY:
            if user_id not in users:
                results.setdefault(money, 0)
                results[money] += 1

            users.add(user_id)

    msg = ""
    for money, count in sorted(results.items(), key=lambda x: x[0]):
        msg += "${}: {}\n".format(money, count)
    msg = msg.strip()

    users = set()
    for row in mode.db_mode.query():
        user_id, creation_datetime, mode = row
        if user_id not in users and mode == "lotto" and user_id == "Ua5f08ec211716ba22bef87a8ac2ca6ee":
            push(user_id, msg)

        users.add(user_id)

def lotto_winner(targets=["Ua5f08ec211716ba22bef87a8ac2ca6ee"]):
    from server.db import mode

    results = {}

    users = set()
    for row in lotto.db_lotto.query():
        user_id, user_name, creation_datetime, money = row
        if money > 0 and money < MONEY:
            if user_id not in users:
                results.setdefault(money, [])
                results[money].append(user_id)

            users.add(user_id)

    winner = None
    for money, users in sorted(results.items(), key=lambda x: x[0]):
        if len(users) == 1:
            winner = line_bot_api.get_profile(users[0])
            break

    for target in targets:
        msg = "恭喜[{}]成為今天最低價得標者".format(winner.display_name.encode("UTF8"))
        push(target, msg)

def random_winner(targets=["Ueb10a8325b1ef3bb256bc30268d4c1aa", "Ua5f08ec211716ba22bef87a8ac2ca6ee", "Ub212ac2cdb7d7bfcfc5d6dfe1b93193c"]):
    users = set()
    for row in lotto.db_lotto.query():
        user_id, user_name, creation_datetime, money = row
        if money > 0 and money < MONEY:
            users.add(user_id)

    winner = line_bot_api.get_profile(random.choice(list(users))).display_name

    for target in targets:
        msg = "此次幸運得主是{}".format(winner)

        push(target, msg)

'''
def run():
    for row in db.db.query():
        user_id, question_type, question = row

        if question_type == "weather":
            answer = "[{}]的天氣狀況如下\n{}".format(question, weather.bot.bots(question))

            push(user_id, answer)
        elif question_type == "bus":
            answer = bus.bot.bots(question)

            push(user_id, answer)
        elif question_type == "lucky":
            answer = "[{}]的你，今天運勢推測如下\n{}".format(question, lucky.bot.bots(question))

            push(user_id, answer)
        else:
            raise NotImplementedError
'''

if __name__ == "__main__":
    #run()
    lotto_results()
    lotto_winner()
    #random_winner()
