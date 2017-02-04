#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import pprint
import datetime

from lib.common.utils import MODE_TICKET
from lib.common.check_taiwan_id import check_taiwan_id_number
from lib.common.mode import Mode
from lib.ticket import booking_tra
from lib.ticket.utils import get_station_number, get_train_type

class TicketMode(Mode):
    memory = {}

    def is_process(self, mode):
        return self.mode.lower() == mode.lower()

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = None
        if user_id not in self.memory or question.lower() in ["reset", "重設", "清空"]:
            self.new_memory(user_id)

        if check_taiwan_id_number(question):
            self.memory[user_id]["person_id"] = question
        elif re.search("([\d]{4})/([\d]{2})/([\d]{2})", question):
            self.memory[user_id]["getin_date"] = "{}-00".format(question)
        elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("getin_start_dtime", None) is None:
            self.memory[user_id]["getin_start_dtime"] = "{:02d}:00".format(int(question))
        elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("getin_end_dtime", None) is None:
            self.memory[user_id]["getin_end_dtime"] = "{:02d}:00".format(int(question))
        elif get_station_number(question) and self.memory[user_id].get("from_station", None) is None:
            self.memory[user_id]["from_station"] = get_station_number(question)
        elif get_station_number(question) and self.memory[user_id].get("to_station", None) is None:
            self.memory[user_id]["to_station"] = get_station_number(question)
        elif question.isdigit() and int(question) > 0 and int(question) < 7 and self.memory[user_id].get("order_qty_str", None) is None:
            self.memory[user_id]["order_qty_str"] = question
        elif get_train_type(question) and self.memory[user_id].get("train_type", None) is None:
            self.memory[user_id]["train_type"] = get_train_type(question)

        if self.memory[user_id].get("person_id", None) is None:
            reply_txt = "請輸入身份證字號(A123456789)"
        elif self.memory[user_id].get("getin_date", None) is None:
            reply_txt = "請輸入欲搭車日期(YYYY/MM/DD)"
        elif self.memory[user_id].get("getin_start_dtime", None) is None:
            reply_txt = "請輸入起始時間(0-23)"
        elif self.memory[user_id].get("getin_end_dtime", None) is None:
            reply_txt = "請輸入終止時間(0-23)"
        elif self.memory[user_id].get("from_station", None) is None:
            reply_txt = "請輸入上車車站"
        elif self.memory[user_id].get("to_station", None) is None:
            reply_txt = "請輸入下車車站"
        elif self.memory[user_id].get("order_qty_str", None) is None:
            reply_txt = "請輸入車票張數"
        elif self.memory[user_id].get("train_type", None) is None:
            reply_txt = "請輸入車種"
        else:
            '''
            ticket_number, ticket_filepath = booking_tra.book_ticket(self.memory[user_id], cropped=1)
            if ticket_number is not None:
                reply_txt = "懶人訂票幫您訂到的台鐵車票號碼是{}".format(ticket_number)
            else:
                reply_txt = "服務忙碌，稍後懶人訂票會繼續幫您服務({})".format(ticket_number)
            '''
            reply_txt = "\n".join(["{}: {}".format(k, v) for k, v in self.memory[user_id]])

            del self.memory[user_id]

        return reply_txt

    def new_memory(self, user_id):
        self.memory.setdefault(user_id, {})
        self.memory[user_id] = {"person_id": None,
                                "creation_datetime": datetime.datetime.now(),
                                "getin_date": None,
                                "from_station": None,
                                "to_station": None,
                                "order_qty_str": None,
                                "train_type": None,
                                "getin_start_dtime": None,
                                "getin_end_dtime": None}

mode_ticket = TicketMode(MODE_TICKET)

if __name__ == "__main__":
    user_id = "L122760167"

    questions = ["我試試", user_id, "2017/02/17", "17", "23", "桃園", "清水", "1", "全部車種"]
    for question in questions:
        print mode_ticket.conversion(question, user_id)
        pprint.pprint(mode_ticket.memory[user_id])
        print
