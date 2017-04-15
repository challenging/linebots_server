#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import datetime

from linebot.models import ConfirmTemplate, MessageTemplateAction, TemplateSendMessage, ButtonsTemplate
from linebot.models import CarouselTemplate, CarouselColumn

from lib.db.profile import db_profile

from lib.common.utils import log, UTF8, MODE_THSR_TICKET
from lib.common.message import txt_not_support, txt_ticket_sstation, txt_ticket_estation, txt_ticket_phone, txt_ticket_retry, txt_ticket_trainno
from lib.common.message import txt_ticket_taiwanid, txt_ticket_getindate, txt_ticket_stime, txt_ticket_etime, txt_ticket_forget, txt_ticket_tra_qty
from lib.common.message import txt_ticket_scheduled, txt_ticket_error, txt_ticket_thankletter, txt_ticket_inputerror, txt_ticket_memory
from lib.common.message import txt_ticket_confirm, txt_ticket_cancel, txt_ticket_zero, txt_ticket_continued, txt_ticket_failed, txt_ticket_train_type

from lib.common.check_taiwan_id import check_taiwan_id_number

from lib.ticket.utils import TICKET_COUNT, thsr_stations
from lib.ticket.utils import TICKET_HEADERS_BOOKED_THSR, TICKET_STATUS_AGAIN, TICKET_STATUS_CONFIRM

from lib.ticket import booking_thsr

from ticket import TicketMode, TicketDB, THSR


class THSRTicketMode(TicketMode):
    def init(self):
        self.memory = {}
        self.db = TicketDB()
        self.ticket_type = THSR

    def conversion_process(self, question, user_id=None, user_name=None):
        reply_txt = None

        if check_taiwan_id_number(question):
            self.memory[user_id]["person_id"] = question.upper()
        elif re.search("^([\+\d]{10,})$", question) and self.memory[user_id].get("cellphone", None) is None:
            self.memory[user_id]["cellphone"] = question
        elif re.search("booking_type=([\w]+)", question):
            m = re.match("booking_type=([\w]+)", question)

            self.memory[user_id]["booking_type"] = m.group(1)
        elif (re.search("([\d]{4})/([\d]{2})/([\d]{2})", question) or re.search("([\d]{8,8})", question)) and self.memory[user_id].get("booking_date", None) is None:
            try:
                booked_date = None
                if question.replace("-", "/").find("/") > -1:
                    booked_date = datetime.datetime.strptime(question, '%Y/%m/%d')
                else:
                    booked_date = datetime.datetime.strptime(question, '%Y%m%d')

                if booked_date > datetime.datetime.now() - datetime.timedelta(days=1):
                    self.memory[user_id]["booking_date"] = booked_date.strftime("%Y/%m/%d")
            except ValueError as e:
                log("Error: {}".format(e))
        elif self.memory[user_id].get("booking_stime", None) is None:
            if re.search("^([\d]{1,2})$", question):
                question = int(question)

                if question > -1 and question < 23:
                    booking_datetime = datetime.datetime.strptime("{} {:02d}".format(self.memory[user_id]["booking_date"], question), "%Y/%m/%d %H")
                    if booking_datetime > datetime.datetime.now() + datetime.timedelta(hours=self.DELAY_HOUR):
                        self.memory[user_id]["booking_stime"] = "{:02d}:00".format(question)
            elif re.search("^([\d]{1,2})-([\d]{1,2})$", question):
                m = re.match("([\d]{1,2})-([\d]{1,2})", question)

                stime, etime = int(m.group(1)), int(m.group(2))
                if stime > -1 and etime > 0 and stime < 23 and etime < 24 and etime > stime:
                    booking_datetime = datetime.datetime.strptime("{} {:02d}".format(self.memory[user_id]["booking_date"], stime), "%Y/%m/%d %H")
                    if booking_datetime > datetime.datetime.now() + datetime.timedelta(hours=self.DELAY_HOUR):
                        self.memory[user_id]["booking_stime"] = "{:02d}:00".format(stime)
                        self.memory[user_id]["booking_etime"] = "{:02d}:00".format(etime)
        elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("booking_etime", None) is None:
            question = int(question)
            if question > 0 and question < 24:
                self.memory[user_id]["booking_etime"] = "{:02d}:00".format(int(question))
        elif question in thsr_stations and self.memory[user_id].get("selectStartStation", None) is None:
            self.memory[user_id]["selectStartStation"] = question
        elif question in thsr_stations and self.memory[user_id].get("selectDestinationStation", None) is None:
            self.memory[user_id]["selectDestinationStation"] = question
        elif self.memory[user_id]["booking_type"] == "student" and re.search("([\d]{1,2})", question) and self.memory[user_id].get("ticketPanel:rows:4:ticketAmount", None) is None:
            question = int(question)

            if question >= 0 and question < 11:
                self.memory[user_id]["ticketPanel:rows:4:ticketAmount"] = question
                self.memory[user_id]["ticketPanel:rows:0:ticketAmount"] = 0
        elif self.memory[user_id]["booking_type"] != "student" and re.search("([\d]{1,2})", question) and self.memory[user_id].get("ticketPanel:rows:0:ticketAmount", None) is None:
            question = int(question)

            if question >= 0 and question < 11:
                self.memory[user_id]["ticketPanel:rows:0:ticketAmount"] = question
        elif self.memory[user_id]["booking_type"] != "student" and re.search("([\d]{1,2})", question) and self.memory[user_id].get("ticketPanel:rows:1:ticketAmount", None) is None:
            question = int(question)

            if question >= 0 and question < 11:
                self.memory[user_id]["ticketPanel:rows:1:ticketAmount"] = question

        if self.memory[user_id].get("person_id", None) is None:
            reply_txt = txt_ticket_taiwanid()
        elif self.memory[user_id].get("cellphone", None) is None:
            reply_txt = txt_ticket_phone()
        elif self.memory[user_id].get("booking_type", None) is None:
            template = ConfirmTemplate(text="請選擇訂票身份", actions=[
                MessageTemplateAction(label="一般訂票", text='booking_type=general'),
                MessageTemplateAction(label="學生訂票", text='booking_type=student'),
            ])

            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
        elif self.memory[user_id].get("booking_date", None) is None:
            reply_txt = txt_ticket_getindate()
        elif self.memory[user_id].get("booking_stime", None) is None:
            reply_txt = txt_ticket_stime()
        elif self.memory[user_id].get("booking_etime", None) is None:
            reply_txt = txt_ticket_etime()
        elif self.memory[user_id].get("selectStartStation", None) is None:
            reply_txt = txt_ticket_sstation()
        elif self.memory[user_id].get("selectDestinationStation", None) is None:
            reply_txt = txt_ticket_estation()
        elif self.memory[user_id]["booking_type"] == "student" and self.memory[user_id].get("ticketPanel:rows:4:ticketAmount", None) is None:
            reply_txt = "請輸入學生張數(1-10)"
        elif self.memory[user_id]["booking_type"] != "student" and self.memory[user_id].get("ticketPanel:rows:0:ticketAmount", None) is None:
            reply_txt = "請輸入成人張數(0-10)"
        elif self.memory[user_id]["booking_type"] != "student" and self.memory[user_id].get("ticketPanel:rows:1:ticketAmount", None) is None:
            reply_txt = "請輸入小孩張數(0-10)"
        elif self.is_filled(user_id):
            message = self.translate_ticket(self.ticket_type, self.memory[user_id])

            if question not in ["ticket_{}={}".format(self.ticket_type, TICKET_STATUS_CONFIRM), "ticket_{}={}".format(self.ticket_type, TICKET_STATUS_AGAIN)]:
                template = ConfirmTemplate(text=message, actions=[
                    MessageTemplateAction(label=txt_ticket_confirm(), text='ticket_{}={}'.format(self.ticket_type, TICKET_STATUS_CONFIRM)),
                    MessageTemplateAction(label=txt_ticket_cancel(), text='ticket_{}={}'.format(self.ticket_type, TICKET_STATUS_AGAIN)),
                ])

                reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
            else:
                if question == "ticket_{}={}".format(self.ticket_type, TICKET_STATUS_CONFIRM) and "creation_datetime" in self.memory[user_id]:
                    del self.memory[user_id]["creation_datetime"]

                    cs, ci = self.db.ask(user_id, json.dumps(self.memory[user_id]), self.ticket_type)
                    if ci > 0:
                        reply_txt = txt_ticket_scheduled()
                    else:
                        if cs > TICKET_COUNT-1:
                            reply_txt = txt_ticket_thankletter().format(TICKET_COUNT)
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
        self.memory[user_id] = {"booking_type": None,
                                "creation_datetime": datetime.datetime.now(),
                                "person_id": None,
                                "cellphone": None,
                                "booking_date": None,
                                "booking_stime": None,
                                "booking_etime": None,
                                "selectStartStation": None,
                                "selectDestinationStation": None,
                                "preferred_seat": "seatRadio1",
                                "booking": "bookingMethod1",
                                "onlyQueryOffPeakCheckBox": False,
                                "ticketPanel:rows:0:ticketAmount": None,
                                "ticketPanel:rows:1:ticketAmount": None}

        for row in db_profile.get_profile(user_id, self.ticket_type):
            for k, v in json.loads(row[0]).items():
                if k in self.memory[user_id] and v is not None and v.lower() not in ["none", "null"]:
                    self.memory[user_id][k] = v

    def is_filled(self, user_id):
        is_pass, ticket_count = True, 0

        if self.memory[user_id]["booking_type"] == "student" and "ticketPanel:rows:1:ticketAmount" in self.memory[user_id]:
            del self.memory[user_id]["ticketPanel:rows:1:ticketAmount"]

        for k, v in self.memory[user_id].items():
            if v is None:
                is_pass = False

                break
            else:
                if k.find("Amount") > -1:
                    ticket_count += v

        return is_pass and ticket_count > 0 and ticket_count < 11

mode_thsr_ticket = THSRTicketMode(MODE_THSR_TICKET)

if __name__ == "__main__":
    person_id = "L122760167"
    user_id = "Ua5f08ec211716ba22bef87a8ac2ca6ee"

    questions = ["booking_type=general", person_id, "0921747196", (datetime.datetime.now()+datetime.timedelta(days=7)).strftime("%Y/%m/%d"), "18", "23", "左營", "南港", "1", "0"]
    for question in questions:
        print question
        message = mode_thsr_ticket.conversion(question, user_id)
        if isinstance(message, str):
            print message
        elif isinstance(message, list):
            for m in message:
                print m

    print mode_thsr_ticket.memory[user_id]
