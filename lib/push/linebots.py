#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint
from flask import Flask, request, abort, send_from_directory

from lib.mode.ticket import mode_ticket

from lib.ticket import booking_tra
from lib.ticket.utils import tra_ticket_dir, tra_fail_dir, get_station_name, get_train_name

from lib.common.utils import MODE_NORMAL
from lib.common.utils import channel_secret, channel_access_token, get_rc_id
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

@blueprint.route("/list_tickets")
def list_tickets():
    return collect(mode_ticket.db)

@blueprint.route("/tra_booking")
def push_ticket(user_id=get_rc_id()):
    requests = mode_ticket.db.non_booking()
    for user_id, creation_datetime, param in requests:
        message = None

        ticket_number, ticket_filepath = booking_tra.book_ticket(param)
        if ticket_number is not None:
            mode_ticket.db.book(user_id, creation_datetime, ticket_number)

            url_thumbnail = "https://lazyrc-reply.herokuapp.com/ticket/id={}_ticket={}.jpg".format(param["person_id"], ticket_number)

            txt = ""
            for name, k in [("身份證字號", "person_id"), ("欲搭車日期", "getin_date"), ("起始時間", "getin_start_dtime"), ("終止時間", "getin_end_dtime"),
                            ("上車車站", "from_station"), ("下車車站", "to_station"), ("車票張數", "order_qty_str"), ("車種", "train_type")]:
                if k.find("station") > -1:
                    txt += "{}: {}({})\n".format(name, param[k], get_station_name(param[k]))
                elif k == "train_type":
                    txt += "{}: {}({})\n".format(name, param[k], get_train_name(param[k]))
                else:
                    txt += "{}: {}\n".format(name, param[k])
            txt = txt.strip()

            message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                MessageTemplateAction(label="取消訂票", text='ticket=cancel')]))

            line_bot_api.push_message(user_id, message)

    return "done..."

if __name__ == "__main__":
    #push_carousel()
    push_ticket()
