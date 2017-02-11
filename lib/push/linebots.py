#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lib.mode.ticket import mode_tra_ticket, mode_thsr_ticket

from lib.ticket import booking_tra
from lib.ticket import booking_thsr
from lib.ticket.utils import tra_ticket_dir, tra_fail_dir, get_station_name, get_train_name, TICKET_STATUS_BOOKED

from lib.common.utils import UTF8, MODE_NORMAL
from lib.common.utils import channel_secret, channel_access_token, log
from lib.common.message import txt_not_support

from linebot import LineBotApi

from linebot.models import (
    TextSendMessage, PostbackEvent, PostbackTemplateAction,
    MessageTemplateAction, ConfirmTemplate, TemplateSendMessage
)

# get channel_secret and channel_access_token from your environment variable
line_bot_api = LineBotApi(channel_access_token)

def collect(db):
    questions = []
    for row in db.query():
        questions.append("\t".join(r if isinstance(r, (str, unicode)) else str(r) for r in row))

    return "<br/>".join(questions)

def booking_tra_ticket():
    requests = mode_tra_ticket.db.non_booking("tra")
    for user_id, creation_datetime, param in requests:
        message = None

        ticket_number, ticket_filepath, ticket_info = booking_tra.book_ticket(param)
        if ticket_number is not None:
            mode_tra_ticket.db.book(user_id, creation_datetime, ticket_number, TICKET_STATUS_BOOKED, "tra")

            txt = "電腦代號: {}\n".format(ticket_number)
            train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time = ticket_info
            txt += "車次: {}\n".format(train_number)
            txt += "車種: {}\n".format(train_type.encode(UTF8))
            txt += "起迄站: {} - {}\n".format(start_station.encode(UTF8), end_station.encode(UTF8))
            txt += "搭乘時間: {} {}\n".format(start_date, start_time)
            txt += "抵達時間 :{} {}".format(end_date, end_time)

            message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                    MessageTemplateAction(label="取消訂票", text='ticket_tra=cancel+{}'.format(ticket_number)),
                    MessageTemplateAction(label="切換模式", text='切換模式')
                ]))

            line_bot_api.push_message(user_id, message)

    return "done..."

def booking_thsr_ticket():
    requests = mode_tra_ticket.db.non_booking("thsr")
    for user_id, creation_datetime, param in requests:
        message = None

        ticket_number, ticket_info = booking_thsr.book_ticket(param, driver="phantom")
        if ticket_number is not None:
            mode_thsr_ticket.db.book(user_id, creation_datetime, ticket_number, TICKET_STATUS_BOOKED, "thsr")

            txt = "電腦代號: {}\n".format(ticket_number)
            train_type, train_count, train_number, start_station, end_station, date, stime, etime, money = ticket_info
            txt += "車次: {}\n".format(train_number)
            txt += "{}\n".format(train_type.encode(UTF8))
            txt += "{}\n".format(train_count.encode(UTF8))
            txt += "起迄站: {} - {}\n".format(start_station.encode(UTF8), end_station.encode(UTF8))
            txt += "搭乘時間: {} {} - {}\n".format(date, stime, etime)
            txt += "付款金額: {} 元".format(money)

            message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                    MessageTemplateAction(label="取消訂票", text='ticket_thsr=cancel+{}'.format(ticket_number)),
                    MessageTemplateAction(label="切換模式", text='切換模式')
                ]))

            line_bot_api.push_message(user_id, message)

    return "done..."

if __name__ == "__main__":
    #booking_tra_ticket()
    booking_thsr_ticket()
