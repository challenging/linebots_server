#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys

from lib.db.mode import db_mode
from lib.bot import fxrate, google_search, weather, lucky, bus
from lib.common.utils import MONEY, UTF8, help, error, get_location

bots_name = ["weather", "lucky", "rate", "bus", "google"]
bots = [lambda msg: weather.bot.bots(msg), lambda msg: lucky.bot.bots(msg), lambda msg: fxrate.bot.bots(msg), lambda msg: bus.bot.bots(msg), lambda msg: google_search.bot.bots(msg)]

def get_mode(msg):
    mode = "normal"

    if msg in ["game", "競標", "競價", "退出", "quit", "正常", "離開"]:
        mode = "special"

    return mode

def mode_special(profile, msg, db_mode):
    if msg in ["game", "競標", "競價"]:
        mode = "lotto"
        msg = "競標"
    else:
        mode = "normal"
        msg = "正常"

    db_mode.ask(profile.user_id, mode)

    reply_txt = "您已將模式設定為[{}]模式".format(msg)

    return reply_txt

def lotto(profile, lotto_opened, msg, db_lotto):
    if lotto_opened:
        if msg.isdigit():
            fee = int(msg)
            if fee > 0 and fee < MONEY:
                 db_lotto.ask(profile.user_id, profile.display_name.encode(UTF8), fee)

                 count = 0
                 users = set()
                 for row in db_lotto.query():
                     user_id, user_name, creation_datetime, money = row
                     if money > 0 and money < MONEY:
                        if user_id not in users and fee == money:
                            count += 1

                        users.add(user_id)

                 reply_txt = "您現今競標的金額是 {} 元(有{}人與您出價相同)".format(fee, count-1)
            elif fee >= MONEY:
                 reply_txt = "金額需要小於{}元，不然你請大家喝飲料好了，謝謝！".format(MONEY)
        else:
            reply_txt = "請輸入正整數型態（不要耍笨，輸入這鬼東西[{}]）".format(msg)
    else:
        reply_txt = "[競標]時間到，不再接受競標。"

    return reply_txt

def mode_normal(profile, msg, mode, db_mode, db_location, db_question, db_lotto, lotto_opened=True):
    for row in db_mode.query(profile.user_id):
        user_id, creation_datetime, mode = row

        break

    if mode == "normal":
        reply_txt = help()
        find_answer = False

        # get location
        state = None
        for row in db_location.query(profile.user_id):
            print "{}'s location is at {}".format(profile.display_name.encode(UTF8), row),
            _, _, lat, lng = row

            g = get_location(lat, lng)
            state = g.state if g.state else g.county

            print "{} base on ({},{})".format(state, lat, lng)

            break

        # get lucky
        twelve = None

        if re.search(r"^(help|幫助)$", msg):
            find_answer = True
        elif msg in ["weather", "天氣"]:
            if state:
                print "weather mode: ", state

                reply_txt = bots[bots_name.index("weather")](state)
            else:
                reply_txt = "尚無設定地理位置，請設定後，即可得到正確天氣資訊。"

            find_answer = True
        elif msg in ["lucky", "星座"] and twelve:
            print "lucky mode: ", twelve

            answer = bots[bots_name.index("lucky")](twelve)
            if anwer is not None:
                reply_txt = answer
            else:
                reply_txt = "尚無設定星座，請設定後，即可得到星座運勢。"

            find_answer = True
        else:
            print "Not found the quickly matching keyword"

        if not find_answer:
            for name, bot in zip(bots_name, bots):
                print "{} mode: {}".format(name, msg)

                answer = bot(msg)
                if answer:
                    reply_txt = answer

                    break
        else:
            pass

        db_question.ask(profile.user_id, profile.display_name, msg, reply_txt)
        reply_txt = "嗨！ {},\n{}".format(profile.display_name.encode(UTF8), reply_txt)
    else:
        reply_txt = lotto(profile, lotto_opened, msg, db_lotto)

    return reply_txt

if __name__ == "__main__":
    for bot_name, f in zip(bots_name, bots):
        answer = f(sys.argv[1])
        if answer:
            print bot_name
            print answer

            break
