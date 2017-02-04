#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys

from linebot.models import (
    TemplateSendMessage, CarouselTemplate, CarouselColumn, URITemplateAction,
    ButtonsTemplate, PostbackTemplateAction
)

from lib.db.mode import db_mode
from lib.bot import fxrate, google_search, weather, lucky, bus, place
from lib.common.utils import MONEY, UTF8, get_location
from lib.common.message import txt_help, txt_not_support, txt_article, txt_google, txt_mode, txt_hello
from lib.common.message import txt_ticket, txt_ticket_title, txt_ticket_body
from lib.common.message import txt_error_location, txt_error_lucky

# init bots
place.bot.init()

bots_name = ["weather", "lucky", "rate", "bus", "place", "google"]
bots = [lambda msg: weather.bot.bots(msg),
        lambda msg: lucky.bot.bots(msg),
        lambda msg: fxrate.bot.bots(msg),
        lambda msg: bus.bot.bots(msg),
        lambda msg: place.bot.bots(msg),
        lambda msg: google_search.bot.bots(msg)]

MODE_NORMAL = "normal"
MODE_SPECIAL = "special"
MODE_LOTTO = "lotto"

DEFINED_GAME_START_WORD = set(["game", "競標", "競價"])
DEFINED_GAME_END_WORD = set(["退出", "quit", "正常", "離開"])
DEFINED_GAME_WORD = DEFINED_GAME_START_WORD.union(DEFINED_GAME_END_WORD)

KEYWORD_TICKET = set(["懶人訂票"])
KEYWORD_LUCKY = set(["lucky", "星座"])
KEYWORD_WEATHER = set(["weather", "天氣"])

def get_mode(msg):
    global MODE_NORMAL
    global DEFINED_GAME_WORD

    mode = MODE_NORMAL
    if msg in DEFINED_GAME_WORD:
        mode = MODEL_SPECIAL

    return mode

def mode_special(profile, msg, db_mode):
    global MODE_LOTTO, MODE_TICKET
    global DEFINED_GAME_START_WORD

    if msg in DEFINED_GAME_START_WORD:
        mode = MODE_LOTTO
        msg = "競標"
    else:
        mode = MODE_NORMAL
        msg = "正常"

    db_mode.ask(profile.user_id, mode)

    return txt_mode(msg)

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
    global MODE_NORMAL, MODE_LOTTO
    global KEYWORD_TICKET, KEYWORD_LUCKY, KEYWORD_WEATHER

    for row in db_mode.query(profile.user_id):
        user_id, creation_datetime, mode = row

        break

    reply_txt = txt_help()
    if mode == MODE_NORMAL:
        find_answer = False

        # get location
        latlng, state = None, None
        for row in db_location.query(profile.user_id):
            print "{}'s location is at {}".format(profile.display_name.encode(UTF8), row),
            _, _, lat, lng = row
            latlng = (lat, lng)

            g = get_location(lat, lng)
            state = g.state if g.state else g.county

            print "{} base on ({},{})".format(state, lat, lng)

            break

        # get lucky
        twelve = None
        if msg in KEYWORD_TICKET:
            buttons = ButtonsTemplate(
                title=txt_ticket_title(), text=txt_ticket_body(), actions=[
                    PostbackTemplateAction(label=txt_ticket("tra"), data='ticket=tra'),
                    PostbackTemplateAction(label=txt_ticket("thsr"), data='ticket=thsr'),
                    PostbackTemplateAction(label=txt_ticket("fly"), data='ticket=fly')
                ])

            reply_txt = TemplateSendMessage(
                alt_text=txt_not_support(), template=buttons)

            find_answer = True
        elif re.search(r"^(help|幫助)$", msg):
            find_answer = True
        elif msg in KEYWORD_WEATHER:
            if state:
                print "weather mode: ", state

                reply_txt = bots[bots_name.index("weather")](state)
            else:
                reply_txt = txt_error_location

            find_answer = True
        elif msg in KEYWORD_LUCKY and twelve:
            print "lucky mode: ", twelve

            answer = bots[bots_name.index("lucky")](twelve)
            if anwer is not None:
                reply_txt = answer
            else:
                reply_txt = txt_error_lucky()

            find_answer = True
        else:
            print "Not found the quickly matching keyword"

        if not find_answer:
            for name, bot in zip(bots_name, bots):
                print "{} mode: {}".format(name, msg)

                if name == "place" and latlng:
                    answer = bot((latlng, msg))
                else:
                    answer = bot(msg)

                if answer:
                    if name == "place":
                        reply_txt = TemplateSendMessage(
                            alt_text=txt_not_support(),
                            template=CarouselTemplate(
                                columns=[
                                    CarouselColumn(
                                       thumbnail_image_url=row["image"],
                                        title=row["name"],
                                        text=row["address"],
                                        actions=[
                                            URITemplateAction(
                                                label=txt_article(),
                                                uri=row["uri"]
                                                )
                                            ]
                                        ) for idx, row in enumerate(answer)
                                    ]
                                )
                            )
                    elif name == "google":
                        reply_txt = txt_google(msg, answer)
                    else:
                        reply_txt = answer

                    break
                else:
                    print "Not found answer for {} based on {} mode".format(msg, name)
        else:
            pass

        if isinstance(reply_txt, (str, unicode)):
            db_question.ask(profile.user_id, profile.display_name, msg, reply_txt)
            reply_txt = txt_hello(profile.display_name.encode(UTF8), reply_txt)
    elif mode == MODE_LOTTO:
        reply_txt = lotto(profile, lotto_opened, msg, db_lotto)

    return reply_txt

if __name__ == "__main__":
    place.bot.init()

    latlng = (25.0408094, 121.5698777)
    question = sys.argv[1]

    for bot_name, f in zip(bots_name, bots):
        if bot_name == "place":
            answer = f((latlng, question))
        else:
            answer = f(question)

        if answer:
            print bot_name
            print answer

            break
