#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys

from linebot.models import (
    TemplateSendMessage, CarouselTemplate, CarouselColumn, URITemplateAction,
    ButtonsTemplate, PostbackTemplateAction
)

from lib.mode.lotto import mode_lotto

from lib.bot import fxrate, google_search, weather, lucky, bus, place

from lib.common.utils import get_location, log
from lib.common.utils import UTF8, MODE_NORMAL, MODE_TRA_TICKET, MODE_THSR_TICKET

from lib.common.message import txt_help, txt_not_support, txt_article, txt_google, txt_hello, txt_location
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

KEYWORD_TICKET = set(["懶人訂票"])
KEYWORD_LUCKY = set(["lucky", "星座"])
KEYWORD_WEATHER = set(["weather", "天氣"])

def mode_change_button():
    message = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(
        title="歡迎使用懶人RC機器人", text="請選擇以下模式", actions=[
            PostbackTemplateAction(label="查詢模式", data='mode={}'.format(MODE_NORMAL)),
            PostbackTemplateAction(label="台鐵訂票模式", data='mode={}'.format(MODE_TRA_TICKET)),
            PostbackTemplateAction(label="高鐵訂票模式", data='mode={}'.format(MODE_THSR_TICKET))
        ]))

    return message

def run_normal(profile, msg, mode, db_mode, db_location, db_question):
    global KEYWORD_TICKET, KEYWORD_LUCKY, KEYWORD_WEATHER

    reply_txt = txt_help()
    find_answer = False

    # get location
    latlng, state = None, None
    for row in db_location.query(profile.user_id):
        log("{}'s location is at {}".format(profile.display_name.encode(UTF8), row),)
        _, _, lat, lng = row
        latlng = (lat, lng)

        g = get_location(lat, lng)
        state = g.state if g.state else g.county

        log("{} base on ({},{})".format(state, lat, lng))

        break

    # get lucky
    twelve = None
    if re.search(r"^(help|幫助)$", msg):
        find_answer = True
    elif msg in KEYWORD_WEATHER:
        if state:
            log("weather mode: {}".format(state))

            reply_txt = bots[bots_name.index("weather")](state)
        else:
            reply_txt = txt_error_location()

        find_answer = True
    elif msg in KEYWORD_LUCKY and twelve:
        log("lucky mode: ".format(twelve))

        answer = bots[bots_name.index("lucky")](twelve)
        if anwer is not None:
            reply_txt = answer
        else:
            reply_txt = txt_error_lucky()

        find_answer = True
    else:
        log("Not found the quickly matching keyword")

    if not find_answer:
        for name, bot in zip(bots_name, bots):
            log("{} mode: {}".format(name, msg))

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
                                            ),
                                        PostbackTemplateAction(
                                            label=txt_location(),
                                            data="t={},a={},lt={},lg={}".format(\
                                                row["name"].encode(UTF8),
                                                row["address"].encode(UTF8),
                                                row["location"][0],
                                                row["location"][1]),
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
                log("Not found answer for {} based on {} mode".format(msg, name))

    if isinstance(reply_txt, (str, unicode)):
        db_question.ask(profile.user_id, profile.display_name, msg, reply_txt)
        reply_txt = txt_hello(profile.display_name.encode(UTF8), reply_txt)

    return reply_txt

if __name__ == "__main__":
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
