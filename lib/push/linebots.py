#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import requests

from flask import Blueprint
from flask import Flask, request, abort, send_from_directory

from lib.mode.ticket import mode_ticket

from lib.ticket import booking_tra
from lib.ticket.utils import tra_ticket_dir, tra_fail_dir, get_station_name, get_train_name, TICKET_STATUS_BOOKED

from lib.common.utils import UTF8, MODE_NORMAL
from lib.common.utils import channel_secret, channel_access_token
from lib.common.message import txt_not_support

from linebot import LineBotApi

from linebot.models import (
    TextSendMessage, PostbackEvent, PostbackTemplateAction,
    MessageTemplateAction, ConfirmTemplate, TemplateSendMessage
)

blueprint = Blueprint('LINEBOTS_PUSH', __name__)

# get channel_secret and channel_access_token from your environment variable
line_bot_api = LineBotApi(channel_access_token)

def collect(db):
    questions = []
    for row in db.query():
        questions.append("\t".join(r if isinstance(r, (str, unicode)) else str(r) for r in row))

    return "<br/>".join(questions)

@blueprint.route("/")
def root():
    return "LINEBOTS - Pushing Service"

@blueprint.route("/ticket/<path:path>")
def ticket(path):
    return send_from_directory(tra_ticket_dir(), path)

@blueprint.route("/fail/<path:path>")
def fail(path):
    return send_from_directory(tra_fail_dir(), path)

def push(user_id, reply_txt):
    line_bot_api.push_message(user_id, TextSendMessage(text=reply_txt))

'''
@blueprint.route("/list_tickets")
def list_tickets():
    return collect(mode_ticket.db)
'''

def booking():
    requests = mode_ticket.db.non_booking()
    for user_id, creation_datetime, param in requests:
        message = None

        ticket_number, ticket_filepath, ticket_info = booking_tra.book_ticket(param)
        if ticket_number is not None:
            mode_ticket.db.book(user_id, creation_datetime, ticket_number, TICKET_STATUS_BOOKED)

            txt = "電腦代號: {}\n".format(ticket_number)
            train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time = ticket_info
            txt += "車次: {}\n".format(train_number)
            txt += "車種: {}\n".format(train_type.encode(UTF8))
            txt += "搭乘時間: {} {}\n".format(start_date, start_time)
            txt += "起迄站: {} - {}\n".format(start_station.encode(UTF8), end_station.encode(UTF8))
            txt += "抵達時間 :{} {}".format(end_date, end_time)

            message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                    MessageTemplateAction(label="取消訂票", text='ticket=cancel+{}'.format(ticket_number)),
                    MessageTemplateAction(label="切換模式", text='切換模式')
                ]))

            line_bot_api.push_message(user_id, message)

    return "done..."

@blueprint.route("/tra_booking")
def push_ticket():
    return booking()

if __name__ == "__main__":
    push_ticket()
