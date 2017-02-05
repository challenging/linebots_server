#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lib.db.question import db_question
from lib.db.location import db_location
from lib.db.mode import db_mode

from lib.mode.ticket import mode_ticket
from lib.ticket import booking_tra

from lib.message_route import run_normal
from lib.common.utils import UTF8, MODE_NORMAL
from lib.common.utils import channel_secret, channel_access_token, get_rc_id

from linebot import LineBotApi

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    CarouselTemplate, CarouselColumn, PostbackEvent, PostbackTemplateAction, URITemplateAction,
    MessageTemplateAction, TemplateSendMessage,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage
)

from lib.push import db

# get channel_secret and channel_access_token from your environment variable
line_bot_api = LineBotApi(channel_access_token)

def push(user_id, reply_txt):
    line_bot_api.push_message(user_id, TextSendMessage(text=reply_txt))

def push_carousel(user_id=get_rc_id()):
    profile = line_bot_api.get_profile(user_id)

    message = mode_normal(profile, "cafe", MODE_NORMAL, db_mode, db_location, db_question)
    line_bot_api.push_message(user_id, message)

def push_ticket(user_id=get_rc_id()):
    requests = mode_ticket.db.non_booking()
    for user_id, creation_datetime, param in requests:
        message = None

        ticket_number, ticket_filepath = booking_tra.book_ticket(param)
        if ticket_number is not None:
            message = ticket_number
            mode_ticket.db.book(user_id, creation_datetime, ticket_number)

            line_bot_api.push_message(user_id, TextSendMessage(text="您的台鐵車票號碼是{}".format(message)))

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

if __name__ == "__main__":
    #push_carousel()
    push_ticket()
