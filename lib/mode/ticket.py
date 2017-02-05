#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import pprint
import datetime

from linebot.models import ConfirmTemplate, MessageTemplateAction, TemplateSendMessage

from lib.common.mode import Mode
from lib.common.db import DB

from lib.common.utils import MODE_TICKET
from lib.common.message import txt_not_support
from lib.common.check_taiwan_id import check_taiwan_id_number
from lib.ticket.utils import get_station_number, get_train_type

class TRATicketDB(DB):
    table_name = "ticket"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), creation_datetime TIMESTAMP, ticket_type VARCHAR(32), ticket VARCHAR(1024), ticket_number INTEGER);".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (ticket_type, creation_datetime, ticket_number);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, ticket_type, ticket):
        sql = "INSERT INTO {} VALUES('{}', '{}', '{}', '{}', -1);".format(\
            self.table_name, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, ticket)

        cursor = self.conn.cursor()
        cursor.execute(sql)
        cursor.close()

class TicketMode(Mode):
    memory = {}

    def init(self):
        self.db = TRATicketDB()

    def is_process(self, mode):
        return self.mode.lower() == mode.lower()

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = None
        if user_id not in self.memory or question.lower() in ["reset", "重設", "清空"]:
            self.new_memory(user_id)

        if check_taiwan_id_number(question):
            self.memory[user_id]["person_id"] = question
        elif re.search("([\d]{4})/([\d]{2})/([\d]{2})", question):
            booked_date = datetime.datetime.strptime(question, '%Y/%m/%d')

            if booked_date > datetime.datetime.now():
                self.memory[user_id]["getin_date"] = "{}-00".format(question)
        elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("getin_start_dtime", None) is None:
            question = int(question)

            if question > -1 and question < 24:
                self.memory[user_id]["getin_start_dtime"] = "{:02d}:00".format(int(question))
        elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("getin_end_dtime", None) is None:
            question = int(question)
            diff_dtime = question - int(self.memory[user_id]["getin_start_dtime"].split(":")[0])

            if question > -1 and question < 24 and diff_dtime > 0 and diff_dtime < 9:
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
        elif self.is_filled(user_id):
            message = ""
            for name, k in [("身份證字號", "person_id"), ("欲搭車日期", "getin_date"), ("起始時間", "getin_start_dtime"), ("終止時間", "getin_end_dtime"),
                            ("上車車站", "from_station"), ("下車車站", "to_station"), ("車票張數", "order_qty_str"), ("車種", "train_type")]:
                message += "{}: {}\n".format(name, self.memory[user_id][k])
            message = message.strip()

            if question not in ["ticket=confirm", "ticket=again"]:
                template = ConfirmTemplate(text=message, actions=[
                    MessageTemplateAction(label="確認訂票", text='ticket=confirm'),
                    MessageTemplateAction(label="重新輸入", text='ticket=again'),
                ])

                reply_txt = TemplateSendMessage(
                    alt_text=txt_not_support(), template=template)
            else:
                if question == "ticket=confirm":
                    del self.memory[user_id]["creation_datetime"]
                    self.db.ask(user_id, "tra", json.dumps(self.memory[user_id]))

                    reply_txt = "懶人RC已將您的訂票需求排入排成，一旦訂到票，將會立即通知，感謝使用此服務"
                else:
                    reply_txt = "請輸入身分證號字號"

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

    def is_filled(self, user_id):
        is_pass = True
        for v in self.memory[user_id].values():
            if v is None:
                is_pass = False

                break

        return is_pass

mode_ticket = TicketMode(MODE_TICKET)

if __name__ == "__main__":
    user_id = "L122760167"

    questions = ["我試試", user_id, "2017/01/17", "17", "23", "桃園", "清水", "1", "全部車種", "ticket=confirm"]
    for question in questions:
        print mode_ticket.conversion(question, user_id)
        pprint.pprint(mode_ticket.memory[user_id])
        print
