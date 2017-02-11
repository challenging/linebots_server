#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import requests
import datetime

from linebot.models import ConfirmTemplate, MessageTemplateAction, TemplateSendMessage
from linebot.models import PostbackTemplateAction, ButtonsTemplate

from lib.common.mode import Mode
from lib.common.db import DB

from lib.common.utils import MODE_TRA_TICKET, MODE_THSR_TICKET, log
from lib.common.message import txt_not_support
from lib.common.check_taiwan_id import check_taiwan_id_number

from lib.ticket.utils import thsr_stations
from lib.ticket.utils import get_station_number, get_station_name, get_train_type, get_train_name
from lib.ticket.utils import tra_train_type, TICKET_STATUS_CANCELED, TICKET_STATUS_SCHEDULED

from lib.ticket.booking_thsr import cancel_ticket

class TicketDB(DB):
    table_name = "ticket"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), creation_datetime TIMESTAMP, ticket_type VARCHAR(32), ticket VARCHAR(1024), ticket_number VARCHAR(32), status VARCHAR(16));".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (ticket_type, creation_datetime, ticket_number);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, ticket, ticket_type):
        sql = "INSERT INTO {} VALUES('{}', '{}', '{}', '{}', -1, 'scheduled');".format(\
            self.table_name, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, ticket)

        cursor = self.conn.cursor()
        cursor.execute(sql)
        cursor.close()

    def non_booking(self, ticket_type, status=TICKET_STATUS_SCHEDULED):
        booking_date, diff_days = None, None
        if ticket_type == "tra":
            diff_days = 14
            booking_date = "cast(cast(ticket::json->'getin_date' as varchar) as date)"
        elif ticket_type == "thsr":
            diff_days = 28
            booking_date = "cast(cast(ticket::json->'booking_date' as varchar) as date)"

        now = datetime.datetime.now() - datetime.timedelta(hours=8)
        sql = "SELECT user_id, creation_datetime, ticket FROM {} WHERE ticket_number = '-1' AND creation_datetime > '{}' AND {} BETWEEN '{}' AND '{}' AND status = '{}' AND ticket_type = '{}'".format(\
            self.table_name, now.strftime("%Y-%m-%dT00:00:00"), booking_date, now.strftime("%Y-%m-%dT00:00:00"), (now + datetime.timedelta(days=diff_days)).strftime("%Y-%m-%dT00:00:00"), status, ticket_type)

        print sql

        cursor = self.conn.cursor()
        cursor.execute(sql)

        requests = []
        for row in cursor.fetchall():
            requests.append([row[0], row[1], json.loads(row[2])])

        cursor.close()

        return requests

    def book(self, user_id, creation_datetime, ticket_number, status, ticket_type):
        sql = "UPDATE {} SET ticket_number = '{}', status = '{}' WHERE user_id = '{}' and creation_datetime = '{}' AND ticket_type = '{}'".format(\
            self.table_name, ticket_number, status, user_id, creation_datetime, ticket_type)

        cursor = self.conn.cursor()
        done = cursor.execute(sql)
        cursor.close()

        return done

    def cancel(self, user_id, ticket_number, ticket_type):
        sql = "UPDATE {} SET status = '{}' WHERE user_id = '{}' and ticket_number = '{}' AND ticket_type = '{}'".format(\
            self.table_name, TICKET_STATUS_CANCELED, user_id, ticket_number, ticket_type)

        cursor = self.conn.cursor()
        done = cursor.execute(sql)
        cursor.close()

        return done

    def get_person_id(self, user_id, ticket_number, ticket_type):
        sql = "SELECT ticket::json->'person_id' as uid FROM {} WHERE user_id = '{}' and ticket_number = '{}' AND ticket_type = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(\
            self.table_name, user_id, ticket_number, ticket_type)

        print sql

        person_id = None

        cursor = self.conn.cursor()
        cursor.execute(sql)
        for row in cursor.fetchall():
            person_id = row[0]

        cursor.close()

        return person_id

class TRATicketMode(Mode):
    def init(self):
        self.memory = {}
        self.db = TicketDB()
        self.ticket_type = "tra"

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = None
        if user_id not in self.memory or question.lower() in ["reset", "重設", "清空"]:
            self.new_memory(user_id)

        if re.search("ticket_tra=cancel\+([\d]{6,})", question):
            m = re.match("ticket_tra=cancel\+([\d]{6,})", question)
            ticket_number = m.group(1)

            person_id = self.db.get_person_id(user_id, ticket_number, self.ticket_type)
            requests.get("http://railway.hinet.net/ccancel_rt.jsp?personId={}&orderCode={}".format(person_id, ticket_number))

            self.db.cancel(user_id, ticket_number, self.ticket_type)
            reply_txt = "已經取消號碼為{}的台鐵車票".format(ticket_number)
        else:
            if check_taiwan_id_number(question):
                self.memory[user_id]["person_id"] = question.upper()
            elif re.search("([\d]{4})/([\d]{2})/([\d]{2})", question) and self.memory[user_id].get("getin_date", None) is None:
                try:
                    booked_date = datetime.datetime.strptime(question, '%Y/%m/%d')

                    if booked_date > datetime.datetime.now():
                        self.memory[user_id]["getin_date"] = "{}-00".format(question)
                except ValueError as e:
                    log("Error: {}".format(e))
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
                reply_txt = "請輸入張數(1-6)"
            elif self.memory[user_id].get("train_type", None) is None:
                reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(
                                title="請輸入車種",
                                text="What kind of train do you choose?",
                                actions=[MessageTemplateAction(label=k, text=k) for k in tra_train_type.keys()]
                            ))
            elif self.is_filled(user_id):
                message = "台鐵訂票資訊如下\n====================\n"
                for name, k in [("身份證字號", "person_id"), ("欲搭車日期", "getin_date"), ("起始時間", "getin_start_dtime"), ("終止時間", "getin_end_dtime"),
                                ("上車車站", "from_station"), ("下車車站", "to_station"), ("車票張數", "order_qty_str"), ("車種", "train_type")]:
                    if k.find("station") > -1:
                        message += "{}: {}({})\n".format(name, self.memory[user_id][k], get_station_name(self.memory[user_id][k]))
                    elif k == "train_type":
                        message += "{}: {}({})\n".format(name, self.memory[user_id][k], get_train_name(self.memory[user_id][k]))
                    else:
                        message += "{}: {}\n".format(name, self.memory[user_id][k])
                message = message.strip()

                if question not in ["ticket_tra=confirm", "ticket_tra=again"]:
                    template = ConfirmTemplate(text=message, actions=[
                        MessageTemplateAction(label="確認訂票", text='ticket_tra=confirm'),
                        MessageTemplateAction(label="重新輸入", text='ticket_tra=again'),
                    ])

                    reply_txt = TemplateSendMessage(
                        alt_text=txt_not_support(), template=template)
                else:
                    if question == "ticket_tra=confirm":
                        del self.memory[user_id]["creation_datetime"]
                        self.db.ask(user_id, json.dumps(self.memory[user_id]), self.ticket_type)

                        reply_txt = "懶人RC開始為您訂票，若有消息會立即通知，請耐心等候"
                    else:
                        reply_txt = "請輸入身分證號字號"

                    del self.memory[user_id]
            else:
                del self.memory[user_id]

                reply_txt = "輸入資訊有誤，請重新輸入"

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

mode_tra_ticket = TRATicketMode(MODE_TRA_TICKET)

class THSRTicketMode(TRATicketMode):
    def init(self):
        self.memory = {}
        self.db = TicketDB()
        self.ticket_type = "thsr"

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = None
        if user_id not in self.memory or question.lower() in ["reset", "重設", "清空"]:
            self.new_memory(user_id)

        if re.search("ticket_thsr=cancel\+([\d]{6})", question):
            m = re.match("ticket_thsr=cancel\+([\d]{6,})", question)
            ticket_number = m.group(1)

            person_id = self.db.get_person_id(user_id, ticket_number, self.ticket_type)
            is_cancel = cancel_ticket(person_id, ticket_number, driver="phantom")

            if is_cancel:
                self.db.cancel(user_id, ticket_number, self.ticket_type)
                reply_txt = "已經取消號碼為{}的高鐵車票".format(ticket_number)
            else:
                reply_txt = "取消高鐵車票({})失敗，請稍後再試！或者請上高鐵網站取消".format(ticket_number)
        else:
            if check_taiwan_id_number(question):
                self.memory[user_id]["person_id"] = question.upper()
            elif re.search("([\d]{10})", question) and self.memory[user_id].get("cellphone", None) is None:
                self.memory[user_id]["cellphone"] = question
            elif re.search("booking_type=([\w]+)", question):
                m = re.match("booking_type=([\w]+)", question)

                self.memory[user_id]["booking_type"] = m.group(1)
            elif re.search("([\d]{4})/([\d]{2})/([\d]{2})", question) and self.memory[user_id].get("booking_date", None) is None:
                try:
                    booked_date = datetime.datetime.strptime(question, '%Y/%m/%d')

                    if booked_date > datetime.datetime.now():
                        self.memory[user_id]["booking_date"] = question
                except ValueError as e:
                    log("Error: {}".format(e))
            elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("booking_stime", None) is None:
                question = int(question)

                if question > -1 and question < 24:
                    self.memory[user_id]["booking_stime"] = "{:02d}:00".format(int(question))
            elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("booking_etime", None) is None:
                question = int(question)
                diff_dtime = question - int(self.memory[user_id]["booking_stime"].split(":")[0])

                if question > -1 and question < 24 and diff_dtime > 0:
                    self.memory[user_id]["booking_etime"] = "{:02d}:00".format(int(question))
            elif question in thsr_stations and self.memory[user_id].get("selectStartStation", None) is None:
                self.memory[user_id]["selectStartStation"] = question
            elif question in thsr_stations and self.memory[user_id].get("selectDestinationStation", None) is None:
                self.memory[user_id]["selectDestinationStation"] = question
            elif self.memory[user_id]["booking_type"] == "student" and re.search("([\d]{1,2})", question) and self.memory[user_id].get("ticketPanel:rows:4:ticketAmount", None) is None:
                question = int(question)

                if question >= 0 and question < 11:
                    self.memory[user_id]["ticketPanel:rows:4:ticketAmount"] = question
            elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("ticketPanel:rows:0:ticketAmount", None) is None:
                question = int(question)

                if question >= 0 and question < 11:
                    self.memory[user_id]["ticketPanel:rows:0:ticketAmount"] = question
            elif self.memory[user_id]["booking_type"] != "student" and re.search("([\d]{1,2})", question) and self.memory[user_id].get("ticketPanel:rows:1:ticketAmount", None) is None:
                question = int(question)

                if question >= 0 and question < 11:
                    self.memory[user_id]["ticketPanel:rows:1:ticketAmount"] = question

            if self.memory[user_id].get("person_id", None) is None:
                reply_txt = "請輸入身份證字號(A123456789)"
            elif self.memory[user_id].get("cellphone", None) is None:
                reply_txt = "請輸入手機號碼(0912345678)"
            elif self.memory[user_id].get("booking_type", None) is None:
                template = ConfirmTemplate(text="請選擇訂票身份", actions=[
                    MessageTemplateAction(label="一般訂票", text='booking_type=general'),
                    MessageTemplateAction(label="學生訂票", text='booking_type=student'),
                ])

                reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
            elif self.memory[user_id].get("booking_date", None) is None:
                reply_txt = "請輸入欲搭車日期(YYYY/MM/DD)"
            elif self.memory[user_id].get("booking_stime", None) is None:
               reply_txt = "請輸入起始時間(0-23)"
            elif self.memory[user_id].get("booking_etime", None) is None:
                reply_txt = "請輸入終止時間(0-23)"
            elif self.memory[user_id].get("selectStartStation", None) is None:
                reply_txt = "請輸入上車車站"
            elif self.memory[user_id].get("selectDestinationStation", None) is None:
                reply_txt = "請輸入下車車站"
            elif self.memory[user_id]["booking_type"] == "student" and self.memory[user_id].get("ticketPanel:rows:4:ticketAmount", None) is None:
                reply_txt = "請輸入學生張數(1-10)"
            elif self.memory[user_id].get("ticketPanel:rows:0:ticketAmount", None) is None:
                reply_txt = "請輸入成人張數(0-10)"
            elif self.memory[user_id]["booking_type"] != "student" and self.memory[user_id].get("ticketPanel:rows:1:ticketAmount", None) is None:
                reply_txt = "請輸入小孩張數(0-10)"
            elif self.is_filled(user_id):
                message = "高鐵訂票資訊如下\n====================\n"
                for name, k in [("身份證字號", "person_id"), ("手機號碼", "cellphone"), ("欲搭車日期", "booking_date"), ("起始時間", "booking_stime"), ("終止時間", "booking_etime"), ("上車車站", "selectStartStation"), ("下車車站", "selectDestinationStation"), ("成人票張數", "ticketPanel:rows:0:ticketAmount"), ("小孩票張數", "ticketPanel:rows:1:ticketAmount"), ("學生票張數", "ticketPanel:rows:4:ticketAmount")]:
                    if self.memory[user_id].get(k, None) is not None:
                        message += "{}: {}\n".format(name, self.memory[user_id][k])
                message = message.strip()

                if question not in ["ticket_thsr=confirm", "ticket_thsr=again"]:
                    template = ConfirmTemplate(text=message, actions=[
                        MessageTemplateAction(label="確認訂票", text='ticket_thsr=confirm'),
                        MessageTemplateAction(label="重新輸入", text='ticket_thsr=again'),
                    ])

                    reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
                else:
                    if question == "ticket_thsr=confirm":
                        del self.memory[user_id]["creation_datetime"]
                        self.db.ask(user_id, json.dumps(self.memory[user_id]), self.ticket_type)

                        reply_txt = "懶人RC開始為您訂票，若有消息會立即通知，請耐心等候"
                    else:
                        reply_txt = "請輸入身分證號字號"

                    del self.memory[user_id]
            else:
                del self.memory[user_id]

                reply_txt = "輸入資訊有誤，請重新輸入"

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

    '''
    questions = ["我試試", person_id, "2017/02/17", "17", "23", "桃園", "清水", "1", "全部車種"]
    for question in questions:
        message = mode_tra_ticket.conversion(question, person_id)
        if isinstance(message, str):
            print message
        else:
            print message.as_json_string()

    questions = ["我試試", "booking_type=student", person_id, "0921747196", "2017/02/17", "17", "23", "桃園", "台中", "2", "0"]
    for question in questions:
        message = mode_thsr_ticket.conversion(question, person_id)
        if isinstance(message, str):
            print message
        elif message is not None:
            print message.as_json_string()
    '''

    mode_thsr_ticket.conversion("ticket_thsr=cancel+06052042", user_id)
