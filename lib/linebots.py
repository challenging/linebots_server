#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookParser, WebhookHandler
)

from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage
)

from db.question import db_question
from db.location import db_location
from db.mode import db_mode
from db.lotto import db_lotto

from lib.common.utils import get_location, error
from lib.common.utils import UTF8, channel_secret, channel_access_token

from lib.ddt import get_mode, mode_special, mode_normal

lotto_opened = True

blueprint = Blueprint('LINEBOTS', __name__)

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
    print "Get the {}'s location({},{})".format(profile.user_id, lat, lng),

    g = get_location(lat, lng)

    state = g.state if g.state else g.county

    db_location.ask(profile.user_id, lat, lng)

    reply_txt = "現為您的地點設定在 {}".format(state)
    print "location mode: {}".format(state)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_txt)
    )

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    '''
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id=event.message.package_id,
            sticker_id=event.message.sticker_id)
    )
    '''
    pass

@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    global lotto_opened

    # get the basic information about user
    profile = line_bot_api.get_profile(event.source.user_id)
    reply_txt = "嗨, {}!\n{}".format(profile.display_name.encode(UTF8), error())
    msg = event.message.text.encode(UTF8).lower()
    mode = get_mode(msg)

    # set lotto_opened
    is_system_cmd = False
    if profile.user_id == "Ua5f08ec211716ba22bef87a8ac2ca6ee":
        if msg == "game over":
            lotto_opened = False
            is_system_cmd = True

            reply_txt = "關閉競標"
        elif msg == "game start":
            lotto_opened = True
            is_system_cmd = True

            reply_txt = "開啟競標"
        elif msg == "delete game" and not lotto_opened:
            reply_txt = "刪除歷史競標資料"
            is_system_cmd = True

            db_lotto.delete()

        print "receive command to set lotto_opened to be {}".format(lotto_opened)

    if not is_system_cmd:
        if mode == "special":
            reply_txt = mode_special(profile, msg, db_mode)
        elif mode == "normal":
            reply_txt = mode_normal(profile, msg, mode, db_mode, db_location, db_question, db_lotto, lotto_opened)
        else:
            print "Not found this mode({})".format(mode)
        #except Exception as e:
        #    print e

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_txt)
    )
