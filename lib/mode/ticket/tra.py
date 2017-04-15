#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import datetime

from linebot.models import ConfirmTemplate, MessageTemplateAction, TemplateSendMessage, ButtonsTemplate

from lib.db.profile import db_profile
from lib.common.check_taiwan_id import check_taiwan_id_number
from lib.common.utils import log, UTF8, MODE_TRA_TICKET

from ticket import TicketMode, TicketDB
from ticket import TRA

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
            is_setting = self.set_memory(user_id, "person_id", question.upper())
        elif (re.search("([\d]{4})/([\d]{2})/([\d]{2})", question) or re.search("([\d]{8,8})", question)) and self.memory[user_id].get("getin_date", None) is None:
            try:
                booked_date = None
                if question.replace("-", "/").find("/") > -1:
                    booked_date = datetime.datetime.strptime(question, '%Y/%m/%d')
                else:
                    booked_date = datetime.datetime.strptime(question, '%Y%m%d')

                if booked_date > datetime.datetime.now() - datetime.timedelta(days=1):
                    is_setting = self.set_memory(user_id, "getin_date", booked_date.strftime("%Y/%m/%d-00"))
            except ValueError as e:
               log("Error: {}".format(e))
        elif self.memory[user_id].get("tra_mode", None) is None:
            if question.lower() == "ticket_tra_mode=time":
                is_setting = self.set_memory(user_id, "tra_mode", "time")
            elif question.lower() == "ticket_tra_mode=train_no":
                self.memory[user_id]["tra_mode"] = "train_no"
                is_setting = self.set_memory(user_id, "tra_mode", "train_no")
            else:
                pass
        elif self.memory[user_id].get("tra_mode", None) == "time":
            if self.memory[user_id].get("getin_start_dtime", None) is None:
                if re.search("^([\d]{1,2})$", question):
                    question = int(question)

                    if question > -1 and question < 23:
                        booking_datetime = datetime.datetime.strptime("{} {:02d}".format(self.memory[user_id]["getin_date"].split("-")[0], question), "%Y/%m/%d %H")
                        if booking_datetime > datetime.datetime.now() + datetime.timedelta(hours=self.DELAY_HOUR):
                            is_setting = self.set_memory(user_id, "getin_start_dtime", "{:02d}:00".format(question))
                elif re.search("^([\d]{1,2})-([\d]{1,2})$", question):
                    m = re.match("([\d]{1,2})-([\d]{1,2})", question)

                    stime, etime = int(m.group(1)), int(m.group(2))
                    if stime > -1 and etime > 0 and stime < 23 and etime < 24 and etime > stime:
                        booking_datetime = datetime.datetime.strptime("{} {}".format(self.memory[user_id]["getin_date"].split("-")[0], stime), "%Y/%m/%d %H")
                        if booking_datetime > datetime.datetime.now() + datetime.timedelta(hours=self.DELAY_HOUR):
                            is_setting = self.set_memory(user_id, "getin_start_dtime", "{:02d}:00".format(stime))
                            is_setting = self.set_memory(user_id, "getin_end_dtime", "{:02d}:00".format(etime))
            elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("getin_end_dtime", None) is None:
                question = int(question)

                if question > 0 and question < 24 and question > int(self.memory[user_id]["getin_start_dtime"].split(":")[0]):
                    is_setting = self.set_memory(user_id, "getin_end_dtime", "{:02d}:00".format(question))
        elif self.memory[user_id]["tra_mode"].lower() == "train_no":
            if re.search("^[\d]{3,4}$", question) and self.memory[user_id].get("train_no", None) is None and question in self.tra_trains:
                is_setting = self.set_memory(user_id, "train_no", question)

        if not is_setting and get_station_number(question) and self.memory[user_id].get("from_station", None) is None:
            is_setting = self.set_memory(user_id, "from_station", get_station_number(question))
        elif not is_setting and get_station_number(question) and self.memory[user_id].get("to_station", None) is None:
            is_setting = self.set_memory(user_id, "to_station", get_station_number(question))
        elif not is_setting and question.isdigit() and int(question) > 0 and int(question) < 7 and self.memory[user_id].get("order_qty_str", None) is None:
            is_setting = self.set_memory(user_id, "order_qty_str", question)
        elif not is_setting and self.memory[user_id]["tra_mode"] == "time" and get_train_type(question) and self.memory[user_id].get("train_type", None) is None:
            is_setting = self.set_memory(user_id, "train_type", get_train_type(question))

        if self.memory[user_id].get("person_id", None) is None:
            reply_txt = txt_ticket_taiwanid()
        elif self.memory[user_id].get("getin_date", None) is None:
            reply_txt = txt_ticket_getindate()
        elif self.memory[user_id].get("tra_mode", None) is None:
            template = ConfirmTemplate(text=txt_ticket_tra_booking_method(), actions=[
                    MessageTemplateAction(label=txt_ticket_tra_booking_time(), text='ticket_tra_mode=time'),
                    MessageTemplateAction(label=txt_ticket_tra_booking_trainno(), text='ticket_tra_mode=train_no')])

            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
        elif self.memory[user_id].get("tra_mode", None) == "time" and self.memory[user_id].get("getin_start_dtime", None) is None:
            reply_txt = txt_ticket_stime()
        elif self.memory[user_id].get("tra_mode", None) == "time" and self.memory[user_id].get("getin_end_dtime", None) is None:
            reply_txt = txt_ticket_etime()
        elif self.memory[user_id].get("tra_mode", None) == "train_no" and self.memory[user_id].get("train_no", None) is None:
            reply_txt = txt_ticket_trainno()
        elif self.memory[user_id].get("from_station", None) is None:
            reply_txt = txt_ticket_sstation()
        elif self.memory[user_id].get("to_station", None) is None:
            reply_txt = txt_ticket_estation()
        elif self.memory[user_id].get("order_qty_str", None) is None:
            reply_txt = txt_ticket_tra_qty()
        elif self.memory[user_id].get("tra_mode", None) == "time" and self.memory[user_id].get("train_type", None) is None:
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
                    del self.memory[user_id]["creation_datetime"]

                    tra_mode = self.memory[user_id]["tra_mode"]
                    del self.memory[user_id]["tra_mode"]
                    if tra_mode == "time":
                        del self.memory[user_id]["train_no"]
                    elif tra_mode == "train_no":
                        del self.memory[user_id]["getin_start_dtime"]
                        del self.memory[user_id]["getin_end_dtime"]
                        del self.memory[user_id]["train_type"]
                    else:
                        pass

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
        self.memory[user_id] = {"person_id": None,
                                "creation_datetime": datetime.datetime.now(),
                                "tra_mode": None,
                                "train_no": None,
                                "getin_date": None,
                                "from_station": None,
                                "to_station": None,
                                "order_qty_str": None,
                                "train_type": None,
                                "getin_start_dtime": None,
                                "getin_end_dtime": None}

        for row in db_profile.get_profile(user_id, self.ticket_type):
            for k, v in json.loads(row[0]).items():
                if k in self.memory[user_id] and v is not None and v.lower() not in ["none", "null"]:
                    self.memory[user_id][k] = v

    def is_filled(self, user_id):
        is_pass = True
        passing_fields = set()
        if self.memory[user_id].get("tra_mode", None) == "time":
            for field in ["train_no"]:
                passing_fields.add(field)
        elif self.memory[user_id].get("tra_mode", None) == "train_no":
            for field in ["train_type", "getin_start_dtime", "getin_end_dtime"]:
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

    questions = [person_id, "ticket_tra_mode=time", (datetime.datetime.now()+datetime.timedelta(days=7)).strftime("%Y/%m/%d"), "18-23", "台南", "高雄", "1", "全部車種"]#, "ticket_tra=confirm"]
    for question in questions:
        message = mode_tra_ticket.conversion(question, user_id)
        if isinstance(message, str):
            print question
            print message,
        elif isinstance(message, list):
            for m in message:
                print m

    print mode_tra_ticket.memory[user_id]
