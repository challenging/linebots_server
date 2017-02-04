#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys

from linebot.models import (
    TemplateSendMessage, CarouselTemplate, CarouselColumn, URITemplateAction,
    ButtonsTemplate, PostbackTemplateAction
)

from lib.db.mode import db_mode
from lib.mode.lotto import mode_lotto
from lib.bot import fxrate, google_search, weather, lucky, bus, place
from lib.common.utils import UTF8, MODE_NORMAL, MODE_LOTTO, get_location
from lib.common.message import txt_help, txt_not_support, txt_article, txt_google, txt_hello
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

KEYWORD_TICKET = set(["懶人訂票"])
KEYWORD_LUCKY = set(["lucky", "星座"])
KEYWORD_WEATHER = set(["weather", "天氣"])

def mode_change_button(question):
    message = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(
        title="歡迎使用懶人RC機器人", text="請選擇以下模式", actions=[
            PostbackTemplateAction(label="對話模式", data='mode={}'.format(MODE_NORMAL)),
            PostbackTemplateAction(label="訂票模式", data='mode={}'.format(MODE_TICKET)),
            PostbackTemplateAction(label="競標模式", data='mode={}'.format(MODE_LOTTO))
        ]))

    return message

def mode_ticket_button(question):
    buttons = ButtonsTemplate(
        title=txt_ticket_title(), text=txt_ticket_body(), actions=[
            PostbackTemplateAction(label=txt_ticket("tra"), data='ticket=tra'),
            PostbackTemplateAction(label=txt_ticket("thsr"), data='ticket=thsr'),
            PostbackTemplateAction(label=txt_ticket("fly"), data='ticket=fly')
        ])

    return TemplateSendMessage(alt_text=txt_not_support(), template=buttons)

def run_normal(profile, msg, mode, db_mode, db_location, db_question):
    global KEYWORD_TICKET, KEYWORD_LUCKY, KEYWORD_WEATHER

    reply_txt = txt_help()
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
        reply_txt = mode_ticket_button()

        find_answer = True
    elif re.search(r"^(help|幫助)$", msg):
        find_answer = True
    elif msg in KEYWORD_WEATHER:
        if state:
            print "weather mode: ", state

            reply_txt = bots[bots_name.index("weather")](state)
        else:
            reply_txt = txt_error_location()

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
