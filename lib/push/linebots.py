#!/usr/bin/env python
# -*- coding: utf-8 -*-

import linebot
from linebot import LineBotApi

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    CarouselTemplate, CarouselColumn, PostbackEvent, PostbackTemplateAction, URITemplateAction,
    MessageTemplateAction, TemplateSendMessage,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage
)

from lib.push import db

# get channel_secret and channel_access_token from your environment variable
channel_secret = "b7cbe59211c0d67e6b37f7f2ccf43fdc"
channel_access_token = "Toi86OSQGdP6Ss2YVBGTl7eJ91h0z9dYPLVrzjkCQ0TWhd5O7UyTRIGhLYOAhDJBZxxqzavvdL7kAfPdxenlogkah8sucT96Iz7tT6MmMRQ5x5xjek5nzOn8cECZNS1kvCz/8LlrmIKZlxQdP2UgkwdB04t89/1O/w1cDnyilFU="

line_bot_api = LineBotApi(channel_access_token)

def push(user_id, reply_txt):
    #line_bot_api.push_message(user_id, TextSendMessage(text=reply_txt))
    print user_id, reply_txt

def push_carousel(user_id="Ua5f08ec211716ba22bef87a8ac2ca6ee"):
    carousel_template = TemplateSendMessage(
        alt_text='Carousel template',
        template=CarouselTemplate(
            columns=[
                CarouselColumn(
                    thumbnail_image_url='https://s3-us-west-2.amazonaws.com/lineapitest/hamburger_240.jpeg',
                    title='this is menu1',
                    text='description1',
                    actions=[
                        MessageTemplateAction(
                            label='message1',
                            text='message text1'
                        ),
                        URITemplateAction(
                            label='uri1',
                            uri='http://tw.yahoo.com'
                        )
                    ]
                ),
            ]
        )
    )

    try:
        line_bot_api.push_message(user_id, carousel_template)
    except Exception as e:
        print e.message

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
    push_carousel()
