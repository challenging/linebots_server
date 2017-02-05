#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint
from flask import Flask, request, abort, send_from_directory

from lib.linebots import collect

from lib.db.question import db_question
from lib.db.location import db_location
from lib.db.mode import db_mode

from lib.mode.ticket import mode_ticket

from lib.ticket import booking_tra
from lib.ticket.utils import tra_ticket_dir, tra_success_dir, tra_img_dir, tra_fail_dir, tra_screen_dir

from lib.common.utils import MODE_NORMAL
from lib.common.utils import channel_secret, channel_access_token, get_rc_id
from lib.common.message import txt_not_support

from linebot import LineBotApi

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    CarouselTemplate, CarouselColumn, PostbackEvent, PostbackTemplateAction, URITemplateAction,
    MessageTemplateAction, TemplateSendMessage, ImageMessage,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage
)

from lib.push import db

blueprint = Blueprint('LINEBOTS_PUSH', __name__)

# get channel_secret and channel_access_token from your environment variable
line_bot_api = LineBotApi(channel_access_token)

@blueprint.route("/")
def root():
    return "LINEBOTS - Pushing Service"

@blueprint.route("/img/<path:path>")
def img(path):
    return send_from_directory(tra_img_dir(), path)

@blueprint.route("/screenshot/<path:path>")
def screenshot(path):
    return send_from_directory(tra_screen_dir(), path)

@blueprint.route("/ticket/<path:path>")
def ticket(path):
    return send_from_directory(tra_ticket_dir(), path)

@blueprint.route("/fail/<path:path>")
def fail(path):
    return send_from_directory(tra_fail_dir(), path)

def push(user_id, reply_txt):
    line_bot_api.push_message(user_id, TextSendMessage(text=reply_txt))

def push_carousel(user_id=get_rc_id()):
    profile = line_bot_api.get_profile(user_id)

    message = mode_normal(profile, "cafe", MODE_NORMAL, db_mode, db_location, db_question)
    line_bot_api.push_message(user_id, message)

@blueprint.route("/list_tickets")
def list_tickets():
    return collect(mode_ticket.db)

@blueprint.route("/tra_booking")
def push_ticket(user_id=get_rc_id()):
    ticket_count = 0

    requests = mode_ticket.db.non_booking()
    for user_id, creation_datetime, param in requests:
        message = None

        ticket_number, ticket_filepath = booking_tra.book_ticket(param)
        if ticket_number is not None:
            message = ticket_number
            mode_ticket.db.book(user_id, creation_datetime, ticket_number)

            line_bot_api.push_message(user_id, TextSendMessage(text="台鐵車票號碼是{}".format(message)))

            message = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(
                title="以上是您的訂票紀錄", text="If you want to cancel, please click the following button", actions=[
                    PostbackTemplateAction(label="取消", data='action=cancel')
                ]))

            line_bot_api.push_message(user_id, message)

            ticket_count += 1

    return "Get {} tickets".format(ticket_count)

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
