#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from lib.mode.ticket.ticket import TRA, THSR
from lib.mode.ticket.tra import mode_tra_ticket
from lib.mode.ticket.thsr import mode_thsr_ticket

from lib.ticket import booking_tra, booking_thsr
from lib.ticket.utils import (
    TICKET_STATUS_BOOKED, TICKET_STATUS_MEMORY, TICKET_STATUS_CANCELED, TICKET_RETRY, TICKET_STATUS_SCHEDULED, TICKET_STATUS_SPLIT,
    TICKET_STATUS_RETRY, TICKET_STATUS_UNSCHEDULED, TICKET_HEADERS_BOOKED_TRA, TICKET_HEADERS_BOOKED_THSR
)

from lib.common.utils import UTF8, channel_access_token, log
from lib.common.message import txt_not_support, txt_ticket_cancel, txt_ticket_memory, txt_ticket_retry, txt_ticket_split

from linebot import LineBotApi
from linebot.models import MessageTemplateAction, ButtonsTemplate, ConfirmTemplate, TemplateSendMessage

line_bot_api = LineBotApi(channel_access_token)

def booking_tra_ticket(driver="phantom", type=TRA):
    batch_time = 8

    requests = mode_tra_ticket.db.non_booking(type)
    for user_id, param, retry, tid, parent_tid in requests:
        if retry >= TICKET_RETRY:
            mode_tra_ticket.db.set_status(user_id, type, TICKET_STATUS_RETRY, tid=tid)

            number, body, _ = mode_tra_ticket.get_ticket_body((tid, param), type, TICKET_STATUS_SCHEDULED, TICKET_HEADERS_BOOKED_TRA)
            messages = [MessageTemplateAction(label=txt_ticket_retry(), text='ticket_{}={}+{}'.format(type, TICKET_STATUS_RETRY, number)),
                        MessageTemplateAction(label=txt_ticket_cancel(None, None, True), text='ticket_{}={}+{}'.format(type, TICKET_STATUS_UNSCHEDULED, tid))]
            if parent_tid is None:
                messages.append(MessageTemplateAction(label=txt_ticket_split(), text="ticket_{}={}+{}".format(type, TICKET_STATUS_SPLIT, number)))

            line_bot_api.push_message(user_id, TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(text=body, actions=messages)))
        else:
            message, stime, etime = None, 1, 2
            is_time = param.get("train_no", None) is None

            if is_time:
                stime, etime = param["getin_start_dtime"], param["getin_end_dtime"]
                stime, etime = int(stime.split(":")[0]), int(etime.split(":")[0])
                if stime == 23 and etime == 23:
                    etime = 24

            for sdtime in range(stime, etime, batch_time):
                if is_time:
                    if etime != 24:
                        param["getin_start_dtime"], param["getin_end_dtime"] = "{:02d}:00".format(sdtime), "{:02d}:00".format(min(etime, sdtime+batch_time))
                    else:
                        param["getin_start_dtime"], param["getin_end_dtime"] = "{:02d}:00".format(sdtime), "23:59"
                print param

                ticket_number, ticket_filepath, ticket_info = booking_tra.book_ticket(param, driver=driver)
                if ticket_number is not None:
                    train_number, train_type, train_count, start_date, start_time, start_station, end_station, end_date, end_time = ticket_info
                    info = {"票號": ticket_number,
                            "車次/車種": "{}/{}".format(train_number, train_type.encode(UTF8)),
                            "起迄站": "{} - {}, {}張".format(start_station.encode(UTF8), end_station.encode(UTF8), train_count),
                            "搭乘時間": "{} {} - {}".format(start_date, start_time, end_time)}

                    mode_tra_ticket.db.book(tid, ticket_number, TICKET_STATUS_BOOKED, json.dumps(info))

                    if parent_tid is not None:
                        mode_tra_ticket.db.schedule_waitting_ticket(user_id, type, parent_tid, train_number)
                        log("set the status of waitting ticket(train_no={}, parent_id={}, id={}) from waitting to scheduled".format(train_number, parent_tid, tid))

                    txt = "電腦代號: {}\n".format(ticket_number)
                    txt += "{}\n".format("="*20)
                    txt += "車次/車種: {}/{}\n".format(train_number, train_type.encode(UTF8))
                    txt += "起迄站: {} - {}, {}張\n".format(start_station.encode(UTF8), end_station.encode(UTF8), train_count)
                    txt += "搭乘時間: {} {} - {}\n".format(start_date, start_time, end_time)
                    txt += "訂票成功，請自行使用台鐵付款方式"

                    message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                            MessageTemplateAction(label=txt_ticket_cancel(), text='ticket_{}={}+{}'.format(type, TICKET_STATUS_CANCELED, ticket_number)),
                            MessageTemplateAction(label=txt_ticket_memory()[:12], text='ticket_{}={}+{}'.format(type, TICKET_STATUS_MEMORY, ticket_number))
                        ]))

                    line_bot_api.push_message(user_id, message)

                    break
                else:
                    mode_tra_ticket.db.retry(tid)
                    log("fail in retrying to crack the {} ticket for {}".format(type.upper(), user_id))

def booking_thsr_ticket(driver="phantom", type=THSR):
    requests = mode_tra_ticket.db.non_booking(type)
    for user_id, param, retry, tid, parent_tid in requests:
        if retry >= TICKET_RETRY:
            mode_tra_ticket.db.set_status(user_id, type, TICKET_STATUS_RETRY, tid=tid)

            number, body, _ = mode_thsr_ticket.get_ticket_body((tid, param), type, TICKET_STATUS_SCHEDULED, TICKET_HEADERS_BOOKED_THSR)
            messages = [MessageTemplateAction(label=txt_ticket_retry(), text='ticket_{}={}+{}'.format(type, TICKET_STATUS_RETRY, number)),
                        MessageTemplateAction(label=txt_ticket_cancel(None, None, True), text='ticket_{}={}+{}'.format(type, TICKET_STATUS_UNSCHEDULED, tid))]

            line_bot_api.push_message(user_id, TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(text=body, actions=messages)))
        else:
            ticket_number, ticket_info = None, None
            try:
                ticket_number, ticket_info = booking_thsr.book_ticket(param, driver=driver)
            except Exception as e:
                log(e)

            if ticket_number is not None:
                train_type, train_count, train_number, start_station, end_station, date, stime, etime, money = ticket_info
                info = {"票號": ticket_number,
                        "車次": train_number,
                        "車廂": train_type,
                        "票數": train_count,
                        "起迄站": "{} - {}".format(start_station.encode(UTF8), end_station.encode(UTF8)),
                        "搭乘時間": "{}/{} {} - {}".format(param["booking_date"][:4], date, stime, etime),
                        "付款金額": "{} 元".format(money)}

                mode_thsr_ticket.db.book(tid, ticket_number, TICKET_STATUS_BOOKED, json.dumps(info))

                txt = "電腦代號: {}\n".format(ticket_number)
                txt += "{}\n".format("="*20)
                txt += "車次: {}\n".format(train_number)
                txt += "{}\n".format(train_type.encode(UTF8))
                txt += "{}\n".format(train_count.encode(UTF8))
                txt += "起迄站: {} - {}\n".format(start_station.encode(UTF8), end_station.encode(UTF8))
                txt += "搭乘時間: {}/{} {} - {}\n".format(param["booking_date"][:4], date, stime, etime)
                txt += "付款金額: {} 元\n".format(money)
                txt += "訂票成功，請自行使用高鐵付款方式"

                message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=txt, actions=[
                        MessageTemplateAction(label=txt_ticket_cancel(), text='ticket_{}={}+{}'.format(type, TICKET_STATUS_CANCELED, ticket_number)),
                        MessageTemplateAction(label=txt_ticket_memory()[:12], text='ticket_{}={}+{}'.format(type, TICKET_STATUS_MEMORY, ticket_number))
                    ]))

                line_bot_api.push_message(user_id, message)
            else:
                mode_thsr_ticket.db.retry(tid)
                log("fail in retrying to crack the {} ticket for {}".format(type.upper(), user_id))

if __name__ == "__main__":
    booking_tra_ticket("chrome")
    #booking_thsr_ticket("chrome")
