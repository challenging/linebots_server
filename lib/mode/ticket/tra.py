#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import datetime

from linebot.models import ConfirmTemplate, MessageTemplateAction, TemplateSendMessage, ButtonsTemplate

from lib.db.profile import db_profile
from lib.common.check_taiwan_id import check_taiwan_id_number
from lib.common.utils import log, UTF8, MODE_TRA_TICKET

from lib.mode.ticket.ticket import TicketMode, TicketDB, TRA

from lib.common.message import (
    txt_not_support, txt_ticket_sstation, txt_ticket_estation, txt_ticket_retry, txt_ticket_trainno,
    txt_ticket_taiwanid, txt_ticket_getindate, txt_ticket_stime, txt_ticket_etime, txt_ticket_forget, txt_ticket_tra_qty,
    txt_ticket_scheduled, txt_ticket_error, txt_ticket_thankletter, txt_ticket_inputerror,
    txt_ticket_confirm, txt_ticket_cancel, txt_ticket_continued, txt_ticket_failed, txt_ticket_train_type,
    txt_ticket_tra_booking_method, txt_ticket_tra_booking_time, txt_ticket_tra_booking_trainno
)

from lib.ticket.utils import (
    load_tra_trainno, get_station_number, get_station_name, get_train_type, get_train_name, tra_train_type,
    TICKET_STATUS_AGAIN, TICKET_STATUS_CONFIRM, TRAUtils, TICKET_COUNT
)

HOUR_START = 0
HOUR_END = 24
TICKET_AMOUNT_UPPER_LIMIT = 6
TICKET_AMOUNT_LOWER_LIMIT = 1

TRA_MODE = "tra_mode"

CREATION_DATETIME = "creation_datetime"
PERSON_ID = "person_id"
GETIN_DATE = "getin_date"
TRAIN_NO = "train_no"
TRAIN_TIME = "time"
TRAIN_TYPE = "trian_type"
FROM_STATION = "from_station"
TO_STATION = "to_station"
ORDER_QTY_STR = "order_qty_str"
GETIN_START_DTIME = "getin_start_dtime"
GETIN_END_DTIME = "getin_end_dtime"

class TRATicketMode(TicketMode):
    def init(self):
        self.memory = {}
        self.db = TicketDB()
        self.ticket_type = TRA

        self.tra_trains = load_tra_trainno()

    def conversion_process(self, question, user_id=None, user_name=None):
        reply_txt = None
        is_setting = False

        if check_taiwan_id_number(question):
            is_setting = self.set_memory(user_id, PERSON_ID, question.upper())
        elif (re.search("([\d]{4})/([\d]{2})/([\d]{2})", question) or re.search("([\d]{8,8})", question)) and self.memory[user_id].get(GETIN_DATE, None) is None:
            try:
                booked_date = None
                if question.replace("-", "/").find("/") > -1:
                    booked_date = datetime.datetime.strptime(question, '%Y/%m/%d')
                else:
                    booked_date = datetime.datetime.strptime(question, '%Y%m%d')

                if booked_date > datetime.datetime.now() - datetime.timedelta(days=1):
                    is_setting = self.set_memory(user_id, GETIN_DATE, booked_date.strftime("%Y/%m/%d-00"))
            except ValueError as e:
               log("Error: {}".format(e))
        elif self.memory[user_id].get(TRA_MODE, None) is None:
            if question.lower() == "ticket_tra_mode={}".format(TRAIN_TIME):
                is_setting = self.set_memory(user_id, TRA_MODE, TRAIN_TIME)
            elif question.lower() == "ticket_tra_mode={}".format(TRAIN_NO):
                self.memory[user_id][TRA_MODE] = TRAIN_NO
                is_setting = self.set_memory(user_id, TRA_MODE, TRAIN_NO)
            else:
                pass
        elif self.memory[user_id].get(TRA_MODE, None) == TRAIN_TIME:
            if self.memory[user_id].get(GETIN_START_DTIME, None) is None:
                if re.search("^([\d]{1,2})$", question):
                    question = int(question)

                    if question >= HOUR_START and question <= HOUR_END:
                        booking_datetime = datetime.datetime.strptime("{} {:02d}".format(self.memory[user_id][GETIN_DATE].split("-")[0], question), "%Y/%m/%d %H")
                        if booking_datetime > datetime.datetime.now() + datetime.timedelta(hours=self.DELAY_HOUR):
                            is_setting = self.set_memory(user_id, GETIN_START_DTIME, "{:02d}:00".format(question))
                elif re.search("^([\d]{1,2})-([\d]{1,2})$", question):
                    m = re.match("([\d]{1,2})-([\d]{1,2})", question)

                    stime, etime = int(m.group(1)), int(m.group(2))
                    if stime >= HOUR_START and etime > HOUR_START and etime <= HOUR_END and etime > stime:
                        booking_datetime = datetime.datetime.strptime("{} {}".format(self.memory[user_id][GETIN_DATE].split("-")[0], stime), "%Y/%m/%d %H")
                        if booking_datetime > datetime.datetime.now() + datetime.timedelta(hours=self.DELAY_HOUR):
                            is_setting = self.set_memory(user_id, GETIN_START_DTIME, "{:02d}:00".format(stime))
                            is_setting = self.set_memory(user_id, GETIN_END_DTIME, "{:02d}:00".format(etime))
            elif re.search("([\d]{1,2})", question) and self.memory[user_id].get(GETIN_END_DTIME, None) is None:
                question = int(question)

                if question > HOUR_START and question <= HOUR_END and question > int(self.memory[user_id][GETIN_START_DTIME].split(":")[0]):
                    is_setting = self.set_memory(user_id, GETIN_END_DTIME, "{:02d}:00".format(question))
        elif self.memory[user_id][TRA_MODE].lower() == TRAIN_NO:
            if re.search("^[\d]{3,4}$", question) and self.memory[user_id].get(TRAIN_NO, None) is None and question in self.tra_trains:
                is_setting = self.set_memory(user_id, TRAIN_NO, question)

        if not is_setting and get_station_number(question) and self.memory[user_id].get(FROM_STATION, None) is None:
            is_setting = self.set_memory(user_id, FROM_STATION, get_station_number(question))
        elif not is_setting and get_station_number(question) and self.memory[user_id].get(TO_STATION, None) is None:
            is_setting = self.set_memory(user_id, TO_STATION, get_station_number(question))
        elif not is_setting and question.isdigit() and int(question) <= TICKET_AMOUNT_UPPER_LIMIT and int(question) >= TICKET_AMOUNT_LOWER_LIMIT and self.memory[user_id].get(ORDER_QTY_STR, None) is None:
            is_setting = self.set_memory(user_id, ORDER_QTY_STR, question)
        elif not is_setting and self.memory[user_id][TRA_MODE] == TRAIN_TIME and get_train_type(question) and self.memory[user_id].get(TRAIN_TYPE, None) is None:
            is_setting = self.set_memory(user_id, TRAIN_TYPE, get_train_type(question))

        if self.memory[user_id].get(PERSON_ID, None) is None:
            reply_txt = txt_ticket_taiwanid()
        elif self.memory[user_id].get(GETIN_DATE, None) is None:
            reply_txt = txt_ticket_getindate()
        elif self.memory[user_id].get(TRA_MODE, None) is None:
            template = ConfirmTemplate(text=txt_ticket_tra_booking_method(), actions=[
                    MessageTemplateAction(label=txt_ticket_tra_booking_time(), text='ticket_tra_mode={}'.format(TRAIN_TIME)),
                    MessageTemplateAction(label=txt_ticket_tra_booking_trainno(), text='ticket_tra_mode={}'.format(TRAIN_NO))])

            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
        elif self.memory[user_id].get(TRA_MODE, None) == TRAIN_TIME and self.memory[user_id].get(GETIN_START_DTIME, None) is None:
            reply_txt = txt_ticket_stime()
        elif self.memory[user_id].get(TRA_MODE, None) == TRAIN_TIME and self.memory[user_id].get(GETIN_END_DTIME, None) is None:
            reply_txt = txt_ticket_etime()
        elif self.memory[user_id].get(TRA_MODE, None) == TRAIN_NO and self.memory[user_id].get(TRAIN_NO, None) is None:
            reply_txt = txt_ticket_trainno()
        elif self.memory[user_id].get(FROM_STATION, None) is None:
            reply_txt = txt_ticket_sstation()
        elif self.memory[user_id].get(TO_STATION, None) is None:
            reply_txt = txt_ticket_estation()
        elif self.memory[user_id].get(ORDER_QTY_STR, None) is None:
            reply_txt = txt_ticket_tra_qty()
        elif self.memory[user_id].get(TRA_MODE, None) == TRAIN_TIME and self.memory[user_id].get(TRAIN_TYPE, None) is None:
            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(
                title=txt_ticket_train_type(),
                text="What kind of train do you choose?",
                actions=[MessageTemplateAction(label=k, text=k) for k in tra_train_type.keys()]
            ))
        elif self.is_filled(user_id):
            message = self.translate_ticket(self.ticket_type, self.memory[user_id])

            if question not in ["ticket_{}={}".format(self.ticket_type, TICKET_STATUS_CONFIRM), "ticket_{}={}".format(self.ticket_type, TICKET_STATUS_AGAIN)]:
                template = ConfirmTemplate(text=message, actions=[
                    MessageTemplateAction(label=txt_ticket_confirm(), text='ticket_{}={}'.format(self.ticket_type, TICKET_STATUS_CONFIRM)),
                    MessageTemplateAction(label=txt_ticket_cancel(), text='ticket_{}={}'.format(self.ticket_type, TICKET_STATUS_AGAIN)),
                ])

                reply_txt = TemplateSendMessage(
                    alt_text=txt_not_support(), template=template)
            else:
                if question == "ticket_{}={}".format(self.ticket_type, TICKET_STATUS_CONFIRM):
                    del self.memory[user_id][CREATION_DATETIME]

                    tra_mode = self.memory[user_id][TRA_MODE]
                    del self.memory[user_id][TRA_MODE]
                    if tra_mode == TRAIN_TIME:
                        del self.memory[user_id][TRAIN_NO]
                    elif tra_mode == TRAIN_NO:
                        del self.memory[user_id][GETIN_START_DTIME]
                        del self.memory[user_id][GETIN_END_DTIME]
                        del self.memory[user_id][TRAIN_TYPE]
                    else:
                        pass

                    if self.memory[user_id][GETIN_END_DTIME] == "24:00":
                        self.memory[user_id][GETIN_END_DTIME] = "23:59"

                    cs, ci = self.db.ask(user_id, json.dumps(self.memory[user_id]), self.ticket_type)
                    if ci > 0:
                        reply_txt = txt_ticket_scheduled()
                    else:
                        if cs > TICKET_COUNT-1:
                            reply_txt = txt_ticket_thankletter()
                        else:
                            reply_txt = txt_ticket_error()

                self.new_memory(user_id)
                self.conversion_process("", user_id)
        else:
            del self.memory[user_id]

            reply_txt = txt_ticket_inputerror()

        return reply_txt

    def new_memory(self, user_id):
        self.memory.setdefault(user_id, {})
        self.memory[user_id] = {PERSON_ID: None,
                                CREATION_DATETIME: datetime.datetime.now(),
                                TRA_MODE: None,
                                TRAIN_NO: None,
                                GETIN_DATE: None,
                                FROM_STATION: None,
                                TO_STATION: None,
                                ORDER_QTY_STR: None,
                                TRAIN_TYPE: None,
                                GETIN_START_DTIME: None,
                                GETIN_END_DTIME: None}

        for row in db_profile.get_profile(user_id, self.ticket_type):
            for k, v in json.loads(row[0]).items():
                if k in self.memory[user_id] and v is not None and v.lower() not in ["none", "null"]:
                    self.memory[user_id][k] = v

    def is_filled(self, user_id):
        is_pass = True
        passing_fields = set()
        if self.memory[user_id].get(TRA_MODE, None) == TRAIN_TIME:
            for field in [TRAIN_NO]:
                passing_fields.add(field)
        elif self.memory[user_id].get(TRA_MODE, None) == TRAIN_NO:
            for field in [TRAIN_TYPE, GETIN_START_DTIME, GETIN_END_DTIME]:
                passing_fields.add(field)

        for k, v in self.memory[user_id].items():
            if k not in passing_fields and v is None:
                is_pass = False

                break

        return is_pass

mode_tra_ticket = TRATicketMode(MODE_TRA_TICKET)

if __name__ == "__main__":
    person_id = "L122760167"
    user_id = "Ua5f08ec211716ba22bef87a8ac2ca6ee"

    questions = [person_id, "ticket_tra_mode=time", "20170616", "23-24"]
    #questions = [person_id, "ticket_tra_mode=time", (datetime.datetime.now()+datetime.timedelta(days=7)).strftime("%Y/%m/%d"), "18-23", "台南", "高雄", "1", "全部車種"]#, "ticket_tra=confirm"]
    for question in questions:
        message = mode_tra_ticket.conversion(question, user_id)
        if isinstance(message, str):
            print question
            print message,
        elif isinstance(message, list):
            for m in message:
                print m

    print mode_tra_ticket.memory[user_id]
