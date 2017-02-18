#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from lib.mode.ticket import mode_tra_ticket, mode_thsr_ticket

from lib.ticket import booking_tra
from lib.ticket import booking_thsr
from lib.ticket.utils import TICKET_STATUS_BOOKED

from lib.common.utils import UTF8
from lib.common.utils import channel_access_token, log
from lib.common.message import txt_not_support

from linebot import LineBotApi

from linebot.models import (
    TextSendMessage, PostbackEvent, PostbackTemplateAction,
    MessageTemplateAction, ConfirmTemplate, TemplateSendMessage
)

line_bot_api = LineBotApi(channel_access_token)

def collect(db):
    questions = []
    for row in db.query():
        questions.append("\t".join(r if isinstance(r, (str, unicode)) else str(r) for r in row))

    return "<br/>".join(questions)

def booking_tra_ticket(driver="phantom", type="tra"):
    requests = mode_tra_ticket.db.non_booking("tra")
    for user_id, creation_datetime, param in requests:
        message = None

        stime, etime = param["getin_start_dtime"], param["getin_end_dtime"]
        stime, etime = int(stime.split(":")[0]), int(etime.split(":")[0])

        for sdtime in range(stime, etime, 8):
            param["getin_start_dtime"], param["getin_end_dtime"] = "{:02d}:00".format(sdtime), "{:02d}:00".format(min(etime, sdtime+8))
            ticket_number, ticket_filepath, ticket_info = booking_tra.book_ticket(param, driver=driver)
            if ticket_number is not None:
                train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time = ticket_info
                info = {"票號": ticket_number,
                        "車次": train_number,
                        "車種": train_type,
                        "起訖站": "{} - {}".format(start_station.encode(UTF8), end_station.encode(UTF8)),
                        "搭乘時間": "{} {} - {}".format(start_date, start_time, end_time)}

                mode_tra_ticket.db.book(user_id, creation_datetime, ticket_number, TICKET_STATUS_BOOKED, type, json.dumps(info))

                txt = "電腦代號: {}\n".format(ticket_number)
                txt += "{}\n".format("="*20)
                txt += "車次: {}\n".format(train_number)
                txt += "車種: {}\n".format(train_type.encode(UTF8))
                txt += "起迄站: {} - {}\n".format(start_station.encode(UTF8), end_station.encode(UTF8))
                txt += "搭乘時間: {} {} - {}\n".format(start_date, start_time, end_time)
                txt += "訂票成功，請自行使用台鐵付款方式"

                message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                        MessageTemplateAction(label="取消訂票", text='ticket_{}=cancel+{}'.format(type, ticket_number)),
                        MessageTemplateAction(label="繼續訂票", text='ticket_{}=again'.format(type))
                    ]))

                line_bot_api.push_message(user_id, message)

                break

def booking_thsr_ticket(driver="phantom", type="thsr"):
    requests = mode_tra_ticket.db.non_booking("thsr")
    for user_id, creation_datetime, param in requests:
        message = None

        ticket_number, ticket_info = booking_thsr.book_ticket(param, driver=driver)
        if ticket_number is not None:
            train_type, train_count, train_number, start_station, end_station, date, stime, etime, money = ticket_info
            info = {"票號": ticket_number,
                    "車次": train_number,
                    "車廂": train_type,
                    "票數": train_count,
                    "起訖站": "{} - {}".format(start_station.encode(UTF8), end_station.encode(UTF8)),
                    "搭乘時間": "{} {} - {}".format(date, stime, etime),
                    "付款金額": "{} 元".format(money)}

            mode_thsr_ticket.db.book(user_id, creation_datetime, ticket_number, TICKET_STATUS_BOOKED, type, info)

            txt = "電腦代號: {}\n".format(ticket_number)
            txt += "{}\n".format("="*20)
            txt += "車次: {}\n".format(train_number)
            txt += "{}\n".format(train_type.encode(UTF8))
            txt += "{}\n".format(train_count.encode(UTF8))
            txt += "起迄站: {} - {}\n".format(start_station.encode(UTF8), end_station.encode(UTF8))
            txt += "搭乘時間: {} {} - {}\n".format(date, stime, etime)
            txt += "付款金額: {} 元\n".format(money)
            txt += "訂票成功，請自行使用高鐵付款方式"

            message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                    MessageTemplateAction(label="取消訂票", text='ticket_{}=cancel+{}'.format(type, ticket_number)),
                    MessageTemplateAction(label="繼續訂票", text='ticket_{}=again'.format(type))
                ]))

            line_bot_api.push_message(user_id, message)

if __name__ == "__main__":
    user_id = "Ua5f08ec211716ba22bef87a8ac2ca6ee"
    train_type = "thsr"

    #booking_tra_ticket("chrome")
    #booking_thsr_ticket("chrome")

    from lib.push.linebots import mode_thsr_ticket as bot

    print train_type
    messages = bot.list_tickets(user_id, train_type)
    line_bot_api.push_message(user_id, messages)
