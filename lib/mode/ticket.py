#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import time
import requests
import datetime

from linebot.models import ConfirmTemplate, MessageTemplateAction, TemplateSendMessage, ButtonsTemplate
from linebot.models import CarouselTemplate, CarouselColumn

from lib.common.mode import Mode
from lib.common.db import DB

from lib.common.utils import channel_access_token, log
from lib.common.utils import UTF8, MODE_TRA_TICKET, MODE_THSR_TICKET
from lib.common.message import txt_not_support, txt_ticket_sstation, txt_ticket_estation, txt_ticket_phone
from lib.common.message import txt_ticket_taiwanid, txt_ticket_getindate, txt_ticket_stime, txt_ticket_etime
from lib.common.message import txt_ticket_scheduled, txt_ticket_error, txt_ticket_thankletter, txt_ticket_inputerror
from lib.common.message import txt_ticket_confirm, txt_ticket_cancel, txt_ticket_zero

from lib.common.check_taiwan_id import check_taiwan_id_number

from lib.ticket.utils import thsr_stations
from lib.ticket.utils import get_station_number, get_station_name, get_train_type, get_train_name
from lib.ticket.utils import tra_train_type, TICKET_STATUS_BOOKED, TICKET_STATUS_CANCELED, TICKET_STATUS_SCHEDULED, TICKET_STATUS_UNSCHEDULED

from lib.ticket import booking_thsr

class TicketDB(DB):
    table_name = "ticket"

    THRESHOLD_TICKET_COUNT = 3
    DIFF_TRA = 14
    DIFF_THSR = 28

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (id SERIAL, token VARCHAR(256), user_id VARCHAR(128), creation_datetime TIMESTAMP, ticket_type VARCHAR(32), ticket VARCHAR(1024), ticket_number VARCHAR(32), retry INTEGER, status VARCHAR(16));".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx_1 ON {table_name} (token, ticket_type, creation_datetime, ticket_number);".format(table_name=self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx_2 ON {table_name} (token, user_id, ticket_type, ticket_number);".format(table_name=self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx_3 ON {table_name} (id);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, ticket, ticket_type):
        cursor = self.conn.cursor()

        count_select = 0
        sql = "SELECT COUNT(1) FROM {} WHERE ticket_type = '{}' AND status = 'scheduled' AND user_id = '{}'".format(self.table_name, ticket_type, user_id)
        cursor.execute(sql)
        for row in cursor.fetchall():
            count_select = row[0]

        count_insert = 0
        if count_select < self.THRESHOLD_TICKET_COUNT:
            sql = "INSERT INTO {}(token, user_id, creation_datetime, ticket_type, ticket, ticket_number, retry, status) VALUES('{}', '{}', '{}', '{}', '{}', '-1', 0, '{}');".format(\
                self.table_name, channel_access_token, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, ticket, TICKET_STATUS_SCHEDULED)
            cursor.execute(sql)
            count_insert = cursor.rowcount

        cursor.close()

        return count_select, count_insert

    def non_booking(self, ticket_type, status=TICKET_STATUS_SCHEDULED):
        now = datetime.datetime.now() - datetime.timedelta(hours=8)

        booking_date, diff_days = None, None
        if ticket_type == "tra":
            diff_days = self.DIFF_TRA
            booking_date = "cast(cast(ticket::json->'getin_date' as varchar) as date)"

            if now.weekday() == 4:
                diff_days += 2
            elif now.weekday() == 5:
                diff_days += 1
        elif ticket_type == "thsr":
            diff_days = self.DIFF_THSR
            booking_date = "cast(cast(ticket::json->'booking_date' as varchar) as date)"

        sql = "SELECT user_id, creation_datetime, ticket FROM {} WHERE token = '{}' AND ticket_number = '-1' AND {} BETWEEN '{}' AND '{}' AND status = '{}' AND ticket_type = '{}'".format(\
            self.table_name, channel_access_token, booking_date, now.strftime("%Y-%m-%dT00:00:00"), (now + datetime.timedelta(days=diff_days)).strftime("%Y-%m-%dT00:00:00"), status, ticket_type)

        cursor = self.conn.cursor()
        cursor.execute(sql)

        requests = []
        for row in cursor.fetchall():
            requests.append([row[0], row[1], json.loads(row[2])])

        cursor.close()

        return requests

    def book(self, user_id, creation_datetime, ticket_number, status, ticket_type):
        sql = "UPDATE {} SET ticket_number = '{}', status = '{}' WHERE token = '{}' AND user_id = '{}' and creation_datetime = '{}' AND ticket_type = '{}'".format(\
            self.table_name, ticket_number, status, channel_access_token, user_id, creation_datetime, ticket_type)

        cursor = self.conn.cursor()
        done = cursor.execute(sql)
        cursor.close()

        return done

    def unscheduled(self, user_id, tid, status=TICKET_STATUS_UNSCHEDULED):
        sql = "UPDATE {} SET status = '{}' WHERE user_id = '{}' AND id = {}".format(self.table_name, status, user_id, tid)

        cursor = self.conn.cursor()
        cursor.execute(sql)

        count = cursor.rowcount

        cursor.close()

        return count

    def cancel(self, user_id, ticket_number, ticket_type):
        sql = "UPDATE {} SET status = '{}' WHERE token = '{}' AND user_id = '{}' and ticket_number = '{}' AND ticket_type = '{}'".format(\
            self.table_name, TICKET_STATUS_CANCELED, channel_access_token, user_id, ticket_number, ticket_type)

        cursor = self.conn.cursor()
        done = cursor.execute(sql)
        cursor.close()

        return done

    def get_person_id(self, user_id, ticket_number, ticket_type):
        sql = "SELECT ticket::json->'person_id' as uid FROM {} WHERE token = '{}' AND user_id = '{}' and ticket_number = '{}' AND ticket_type = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(\
            self.table_name, channel_access_token, user_id, ticket_number, ticket_type)

        person_id = None

        cursor = self.conn.cursor()
        cursor.execute(sql)
        for row in cursor.fetchall():
            person_id = row[0]

        cursor.close()

        return person_id

    def list_tickets(self, user_id, ticket_type, status=TICKET_STATUS_SCHEDULED):
        cursor = self.conn.cursor()

        sql = "SELECT id, ticket FROM {} WHERE user_id = '{}' AND status = '{}' AND ticket_type = '{}'".format(self.table_name, user_id, status, ticket_type)
        cursor.execute(sql)

        results = []
        for row in cursor.fetchall():
            results.append((row[0], json.loads(row[1])))

        cursor.close()

        return results

class TicketMode(Mode):
    TRA_CANCELED_URL = "http://railway.hinet.net/ccancel_rt.jsp"

    def reset_memory(self, user_id, question):
        if user_id not in self.memory or question.lower() in ["reset", "重設", "清空"]:
            self.new_memory(user_id)

    def cancel_tra_ticket(self, user_id, ticket_number):
        person_id = self.db.get_person_id(user_id, ticket_number, "tra")
        requests.get("{}?personId={}&orderCode={}".format(self.TRA_CANCELED_URL, person_id, ticket_number))

        self.db.cancel(user_id, ticket_number, "tra")

        return txt_ticket_cancel("台鐵", ticket_number)

    def cancel_thsr_ticket(self, user_id, ticket_number):
        person_id = self.db.get_person_id(user_id, ticket_number, "thsr")
        is_cancel = booking_thsr.cancel_ticket(person_id, ticket_number, driver="phantom")

        reply_txt = "取消高鐵車票({})失敗，請稍後再試或請上高鐵網站取消".format(ticket_number)
        if is_cancel:
            self.db.cancel(user_id, ticket_number, "thsr")
            reply_txt = txt_ticket_cancel("高鐵", ticket_number)

        return reply_txt

    def cancel_ticket(self, user_id, ticket_type, ticket_number):
        mode = "未知"
        if ticket_type == "tra":
            mode = "台鐵"
        elif ticket_type == "thsr":
            mode = "高鐵"

        reply_txt = "進入取消{}訂票程序".format(mode)
        if ticket_type == "tra":
            reply_txt = self.cancel_tra_ticket(user_id, ticket_number)
        elif ticket_type == "thsr":
            reply_txt = self.cancel_thsr_ticket(user_id, ticket_number)

        return reply_txt

    def is_cancel_command(self, user_id, question):
        is_cancel, reply_txt = False, None

        p = re.compile("^ticket_(tra|thsr)=cancel\+([\d]{6,})$")
        if p.search(question):
            m = p.match(question)
            ticket_type, ticket_number = m.group(1), m.group(2)

            is_cancel = True
            reply_txt = self.cancel_ticket(user_id, ticket_type, ticket_number)

        return is_cancel, reply_txt

    def is_list_command(self, user_id, question):
        reply_txt = None

        if question in ["query", "查詢", "記錄", "list"]:
            reply_txt = self.list_tickets(user_id, self.ticket_type)

            if reply_txt is None:
                reply_txt = txt_ticket_zero()

        return reply_txt

    def is_unscheduled_command(self, user_id, question):
        id = None

        p = re.compile("^ticket_(thsr|tra)=unscheduled\+([\d]+)$")
        if p.search(question):
            tid = int(p.match(question).group(2))
            count = self.db.unscheduled(user_id, tid)
            if count > 0:
                id = tid

        return id

    def translate_ticket(self, ticket, id=None):
        message = None

        if self.ticket_type == "tra":
            message = self.translate_tra(ticket, id)
        elif self.ticket_type == "thsr":
            message = self.translate_thsr(ticket, id)
        else:
            pass

        return message.strip()

    def translate_tra(self, ticket, id=None):
        message = None
        if id is None:
            message = "台鐵訂票資訊如下\n====================\n"
        else:
            message = "台鐵訂票資訊如下 - {}\n====================\n".format(id)

        for name, k in [("身份證字號", "person_id"), ("欲搭車日期", "getin_date"), ("起始時間", "getin_start_dtime"), ("終止時間", "getin_end_dtime"),
                        ("上車車站", "from_station"), ("下車車站", "to_station"), ("車票張數", "order_qty_str"), ("車種", "train_type")]:
           if k.find("station") > -1:
                message += "{}: {}({})\n".format(name, ticket[k], get_station_name(ticket[k]))
           elif k == "train_type":
                message += "{}: {}({})\n".format(name, ticket[k], get_train_name(ticket[k]))
           else:
                message += "{}: {}\n".format(name, ticket[k])

        return message

    def translate_thsr(self, ticket, id=None):
        message = None
        if id is None:
            message = "高鐵訂票資訊如下\n====================\n"
        else:
            message = "高鐵訂票資訊如下 - {}\n====================\n".format(id)

        for name, k in [("身份證字號", "person_id"), ("手機號碼", "cellphone"), ("欲搭車日期", "booking_date"), ("起始時間", "booking_stime"), ("終止時間", "booking_etime"),
                        ("上車車站", "selectStartStation"), ("下車車站", "selectDestinationStation"),
                        ("成人票張數", "ticketPanel:rows:0:ticketAmount"), ("小孩票張數", "ticketPanel:rows:1:ticketAmount"), ("學生票張數", "ticketPanel:rows:4:ticketAmount")]:
            if ticket.get(k, None) is not None:
                message += "{}: {}\n".format(name, ticket[k].encode(UTF8) if isinstance(ticket[k], unicode) else ticket[k])

        return message

    def list_tickets(self, user_id, ticket_type):
        tickets = self.db.list_tickets(user_id, ticket_type)

        messages = []
        for ticket in tickets:
            body = self.translate_ticket(ticket[1], ticket[0])

            '''
            message = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=body, actions=[
                MessageTemplateAction(label="取消訂票",
                                      text='ticket_{}={}+{}'.format(self.ticket_type, TICKET_STATUS_UNSCHEDULED, ticket[0])),
                MessageTemplateAction(label="繼續訂票",
                                      text='ticket_{}=continue'.format(self.ticket_type)),
            ]))
            '''

            message = CarouselColumn(title="以下是您的訂票紀錄", text="", actions=[
                MessageTemplateAction(label="取消訂票",
                                      text='ticket_{}={}+{}'.format(self.ticket_type, TICKET_STATUS_UNSCHEDULED, ticket[0])),
                MessageTemplateAction(label="繼續訂票",
                                      text='ticket_{}=continue'.format(self.ticket_type)),
            ])

            messages.append(message)

        reply_txt = None
        if messages:
            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=CarouselTemplate(columns=messages))

        return messages if messages else None

class TRATicketMode(TicketMode):
    def init(self):
        self.memory = {}
        self.db = TicketDB()
        self.ticket_type = "tra"

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = None

        self.reset_memory(user_id, question)
        reply_txt = self.is_list_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        tid = self.is_unscheduled_command(user_id, question)
        if tid:
            return "成功取消預訂票 - {}".format(tid)

        is_cancel, reply_txt = self.is_cancel_command(user_id, question)
        if not is_cancel:
            if check_taiwan_id_number(question):
                self.memory[user_id]["person_id"] = question.upper()
            elif (re.search("([\d]{4})/([\d]{2})/([\d]{2})", question) or re.search("([\d]{8,8})", question)) and self.memory[user_id].get("getin_date", None) is None:
                try:
                    booked_date = None
                    if question.replace("-", "/").find("/") > -1:
                        booked_date = datetime.datetime.strptime(question, '%Y/%m/%d')
                    else:
                        booked_date = datetime.datetime.strptime(question, '%Y%m%d')

                    if booked_date > datetime.datetime.now():
                        self.memory[user_id]["getin_date"] = booked_date.strftime("%Y/%m/%d-00")
                except ValueError as e:
                    log("Error: {}".format(e))
            elif self.memory[user_id].get("getin_start_dtime", None) is None:
                if re.search("^([\d]{1,2})$", question):
                    question = int(question)

                    if question > -1 and question < 23:
                        self.memory[user_id]["getin_start_dtime"] = "{:02d}:00".format(int(question))
                elif re.search("^([\d]{1,2})-([\d]{1,2})$", question):
                    m = re.match("([\d]{1,2})-([\d]{1,2})", question)

                    stime, etime = int(m.group(1)), int(m.group(2))
                    if stime > -1 and etime > 0 and stime < 23 and etime < 24 and etime > stime:
                        self.memory[user_id]["getin_start_dtime"] = "{:02d}:00".format(stime)
                        self.memory[user_id]["getin_end_dtime"] = "{:02d}:00".format(etime)
            elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("getin_end_dtime", None) is None:
                question = int(question)

                if question > 0 and question < 24 and question > int(self.memory[user_id]["getin_start_dtime"].split(":")[0]):
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
                reply_txt = txt_ticket_taiwanid()
            elif self.memory[user_id].get("getin_date", None) is None:
                reply_txt = txt_ticket_getindate()
            elif self.memory[user_id].get("getin_start_dtime", None) is None:
               reply_txt = txt_ticket_stime()
            elif self.memory[user_id].get("getin_end_dtime", None) is None:
                reply_txt = txt_ticket_etime()
            elif self.memory[user_id].get("from_station", None) is None:
                reply_txt = txt_ticket_sstation()
            elif self.memory[user_id].get("to_station", None) is None:
                reply_txt = txt_ticket_estation()
            elif self.memory[user_id].get("order_qty_str", None) is None:
                reply_txt = "請輸入張數(1-6)"
            elif self.memory[user_id].get("train_type", None) is None:
                reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(
                    title="請選擇車種",
                    text="What kind of train do you choose?",
                    actions=[MessageTemplateAction(label=k, text=k) for k in tra_train_type.keys()]
                ))
            elif self.is_filled(user_id):
                message = self.translate_ticket(self.memory[user_id])

                if question not in ["ticket_{}=confirm".format(self.ticket_type), "ticket_{}=again".format(self.ticket_type)]:
                    template = ConfirmTemplate(text=message, actions=[
                        MessageTemplateAction(label=txt_ticket_confirm(), text='ticket_{}=confirm'.format(self.ticket_type)),
                        MessageTemplateAction(label=txt_ticket_cancel(), text='ticket_{}=again'.format(self.ticket_type)),
                    ])

                    reply_txt = TemplateSendMessage(
                        alt_text=txt_not_support(), template=template)
                else:
                    if question == "ticket_{}=confirm".format(self.ticket_type):
                        del self.memory[user_id]["creation_datetime"]

                        cs, ci = self.db.ask(user_id, json.dumps(self.memory[user_id]), self.ticket_type)
                        if ci > 0:
                            reply_txt = txt_ticket_scheduled()
                        else:
                            if cs > self.db.THRESHOLD_TICKET_COUNT-1:
                                reply_txt = txt_ticket_thankletter().format(self.db.THRESHOLD_TICKET_COUNT)
                            else:
                                reply_txt = txt_ticket_error()
                    else:
                        reply_txt = txt_ticket_taiwanid()

                    del self.memory[user_id]
            else:
                del self.memory[user_id]

                reply_txt = txt_ticket_inputerror()

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

class THSRTicketMode(TRATicketMode):
    def init(self):
        self.memory = {}
        self.db = TicketDB()
        self.ticket_type = "thsr"

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = None

        self.reset_memory(user_id, question)
        reply_txt = self.is_list_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        tid = self.is_unscheduled_command(user_id, question)
        if tid:
            return "成功取消預訂票 - {}".format(tid)

        is_cancel, reply_txt = self.is_cancel_command(user_id, question)
        if not is_cancel:
            if check_taiwan_id_number(question):
                self.memory[user_id]["person_id"] = question.upper()
            elif re.search("^([\d]{10})$", question) and self.memory[user_id].get("cellphone", None) is None:
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

                    if booked_date > datetime.datetime.now():
                        self.memory[user_id]["booking_date"] = booked_date.strftime("%Y/%m/%d")
                except ValueError as e:
                    log("Error: {}".format(e))
            elif self.memory[user_id].get("booking_stime", None) is None:
                if re.search("^([\d]{1,2})$", question):
                    question = int(question)

                    if question > -1 and question < 23:
                        self.memory[user_id]["booking_stime"] = "{:02d}:00".format(int(question))
                elif re.search("^([\d]{1,2})-([\d]{1,2})$", question):
                    m = re.match("([\d]{1,2})-([\d]{1,2})", question)

                    stime, etime = int(m.group(1)), int(m.group(2))
                    if stime > -1 and etime > 0 and stime < 23 and etime < 24 and etime > stime:
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
            elif re.search("([\d]{1,2})", question) and self.memory[user_id].get("ticketPanel:rows:0:ticketAmount", None) is None:
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
            elif self.memory[user_id].get("ticketPanel:rows:0:ticketAmount", None) is None:
                reply_txt = "請輸入成人張數(0-10)"
            elif self.memory[user_id]["booking_type"] != "student" and self.memory[user_id].get("ticketPanel:rows:1:ticketAmount", None) is None:
                reply_txt = "請輸入小孩張數(0-10)"
            elif self.is_filled(user_id):
                message = self.translate_ticket(self.memory[user_id])

                if question not in ["ticket_{}=confirm".format(self.ticket_type), "ticket_{}=again".format(self.ticket_type)]:
                    template = ConfirmTemplate(text=message, actions=[
                        MessageTemplateAction(label=txt_ticket_confirm(), text='ticket_{}=confirm'.format(self.ticket_type)),
                        MessageTemplateAction(label=txt_ticket_cancel(), text='ticket_{}=again'.format(self.ticket_type)),
                    ])

                    reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
                else:
                    if question == "ticket_{}=confirm".format(self.ticket_type):
                        del self.memory[user_id]["creation_datetime"]

                        cs, ci = self.db.ask(user_id, json.dumps(self.memory[user_id]), self.ticket_type)
                        if ci > 0:
                            reply_txt = txt_ticket_scheduled()
                        else:
                            if cs > self.db.THRESHOLD_TICKET_COUNT-1:
                                reply_txt = txt_ticket_thankletter().format(self.db.THRESHOLD_TICKET_COUNT)
                            else:
                                reply_txt = txt_ticket_error()
                    else:
                        reply_txt = txt_ticket_taiwanid()

                    del self.memory[user_id]
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

mode_tra_ticket = TRATicketMode(MODE_TRA_TICKET)
mode_thsr_ticket = THSRTicketMode(MODE_THSR_TICKET)

if __name__ == "__main__":
    person_id = "L122760167"
    user_id = "Ua5f08ec211716ba22bef87a8ac2ca6ee"

    questions = ["query"]# "ticket_tra=unscheduled+30", person_id, "2017/05/01", "10-22", "桃園", "清水", "1", "全部車種", "ticket_tra=confirm"]
    for question in questions:
        message = mode_tra_ticket.conversion(question, user_id)
        if isinstance(message, str):
            print message
        elif isinstance(message, list):
            for m in message:
                print m
        else:
            print message.as_json_string()

    questions = ["list"]#, "ticket_thsr=unscheduled+31", "booking_type=student", person_id, "0921747196", "2017/06/17", "17", "23", "桃園", "台中", "2", "0", "ticket_thsr=confirm"]
    for question in questions:
        message = mode_thsr_ticket.conversion(question, user_id)
        if isinstance(message, str):
            print message
        elif isinstance(message, list):
            for m in message:
                print m
        elif message is not None:
            print message.as_json_string()

    #mode_thsr_ticket.conversion("ticket_thsr=cancel+06052042", user_id)
