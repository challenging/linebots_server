#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import threading
import requests

from flask import Blueprint
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookParser, WebhookHandler
)

from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage
)

from db.question import db_question
from db.location import db_location
from db.mode import db_mode
from db.lotto import db_lotto

from mode.lotto import mode_lotto
from mode.ticket import mode_tra_ticket, mode_thsr_ticket

from lib.common.utils import get_location, is_admin, log
from lib.common.utils import MODES, UTF8, LINEBOTS, channel_secret, channel_access_token
from lib.common.message import txt_error, txt_hello, txt_mode
from lib.message_route import mode_change_button, run_normal

blueprint = Blueprint(LINEBOTS, __name__)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

def collect(db):
    questions = []
    for row in db.query():
        questions.append("\t".join(r if isinstance(r, (str, unicode)) else str(r) for r in row))

    return "<br/>".join(questions)

@blueprint.route("/")
def root():
    return "LINEBOTS - Hello World!"

@blueprint.route("/question")
def question():
    return collect(db_question)

@blueprint.route("/location")
def location():
    return collect(db_location)

@blueprint.route("/mode")
def mode():
    return collect(db_mode)

@blueprint.route("/lotto")
def lotto():
    return collect(db_lotto)

@blueprint.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    profile = line_bot_api.get_profile(event.source.user_id)
    lat, lng = event.message.latitude, event.message.longitude
    log("Get the {}'s location({},{})".format(profile.user_id, lat, lng),)

    g = get_location(lat, lng)

    state = g.state if g.state else g.county

    db_location.ask(profile.user_id, lat, lng)

    reply_txt = "現為您的地點設定在 {}".format(state)
    log("location mode: {}".format(state))

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_txt)
    )

@handler.add(PostbackEvent)
def handle_postback(event):
    profile = line_bot_api.get_profile(event.source.user_id)

    if re.search("mode=([\w]+)", event.postback.data):
        m = re.match("mode=([\w]+)", event.postback.data)
        mode = m.group(1)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=txt_mode(mode)))
        db_mode.ask(profile.user_id, mode)
    elif re.search("t=(.+),a=(.+),lt=([\d\.]+),lg=([\d\.]+)", event.postback.data):
        m = re.match("t=(.+),a=(.+),lt=([\d\.]+),lg=([\d\.]+)", event.postback.data)

        line_bot_api.reply_message(
            event.reply_token, LocationSendMessage(
                    title=m.group(1), address=m.group(2),
                    latitude=m.group(3), longitude=m.group(4)
                )
            )
    else:
        pass

@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    # get the basic information about user
    profile = line_bot_api.get_profile(event.source.user_id)
    reply_txt = txt_hello(profile.display_name.encode(UTF8), txt_error())
    msg = event.message.text.encode(UTF8).lower()

    mode, message = None, None
    if msg in MODES:
        message = mode_change_button()
    else:
        mode = db_mode.query(profile.user_id)

        # set lotto_opened
        is_system_cmd = False
        if is_admin(profile.user_id):
            if mode_lotto.is_process(mode, msg):
                if mode_lotto.is_open(msg):
                    mode_lotto.lotto_opened = False
                    is_system_cmd = True

                    reply_txt = "關閉競標"
                elif mode_lotto.is_over(msg):
                    mode_lotto.lotto_opened = True
                    is_system_cmd = True

                    reply_txt = "開啟競標"
                elif mode_lotto.is_delete(msg) and not mode_lotto.lotto_opened:
                    reply_txt = "刪除歷史競標資料"
                    is_system_cmd = True

                    db_lotto.delete()
                else:
                    pass
            else:
                pass
        else:
            pass

        if not is_system_cmd:
            if mode_tra_ticket.is_process(mode, msg):
                reply_txt = mode_tra_ticket.conversion(msg, profile.user_id, profile.display_name.encode(UTF8))
            elif mode_thsr_ticket.is_process(mode, msg):
                reply_txt = mode_thsr_ticket.conversion(msg, profile.user_id, profile.display_name.encode(UTF8))
            elif mode_lotto.is_process(mode, msg):
                reply_txt = mode_lotto.conversion(msg, profile.user_id, profile.display_name.encode(UTF8))
            else:
                reply_txt = run_normal(profile, msg, mode, db_mode, db_location, db_question)
        else:
            pass

        if isinstance(reply_txt, str):
            message = TextSendMessage(text=reply_txt)
        else:
            message = reply_txt

    line_bot_api.reply_message(event.reply_token, message)
