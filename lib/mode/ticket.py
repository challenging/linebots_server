#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import time
import urllib2
import datetime

from linebot.models import ConfirmTemplate, MessageTemplateAction, TemplateSendMessage, ButtonsTemplate
from linebot.models import CarouselTemplate, CarouselColumn

from lib.common.mode import Mode
from lib.common.db import DB
from lib.db.profile import db_profile

from lib.common.utils import channel_access_token, log
from lib.common.utils import UTF8, MODE_TRA_TICKET, MODE_THSR_TICKET
from lib.common.message import txt_not_support, txt_ticket_sstation, txt_ticket_estation, txt_ticket_phone
from lib.common.message import txt_ticket_taiwanid, txt_ticket_getindate, txt_ticket_stime, txt_ticket_etime
from lib.common.message import txt_ticket_scheduled, txt_ticket_error, txt_ticket_thankletter, txt_ticket_inputerror
from lib.common.message import txt_ticket_confirm, txt_ticket_cancel, txt_ticket_zero, txt_ticket_continued, txt_ticket_failed

from lib.common.check_taiwan_id import check_taiwan_id_number

from lib.ticket.utils import thsr_stations, get_station_number, get_station_name, get_train_type, get_train_name, tra_train_type
from lib.ticket.utils import TICKET_CMD_QUERY, TICKET_CMD_RESET, TICKET_HEADERS_BOOKED_TRA, TICKET_HEADERS_BOOKED_THSR
from lib.ticket.utils import TICKET_STATUS_BOOKED, TICKET_STATUS_CANCELED, TICKET_STATUS_SCHEDULED, TICKET_STATUS_UNSCHEDULED, TICKET_STATUS_MEMORY
from lib.ticket.utils import TICKET_STATUS_FORGET, TICKET_STATUS_AGAIN, TICKET_STATUS_FAILED, TICKET_STATUS_CONFIRM, TICKET_STATUS_RETRY, TICKET_STATUS_SPLIT

from lib.ticket import booking_thsr

TRA = "tra"
THSR = "thsr"
CTRA = "台鐵"
CTHSR = "高鐵"

TYPE = [TRA, THSR]

class TicketDB(DB):
    table_name = "ticket"

    THRESHOLD_TICKET_COUNT = 5

    DIFF_TRA = 14
    DIFF_THSR = 27

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (id SERIAL, token VARCHAR(256), user_id VARCHAR(128), creation_datetime TIMESTAMP, ticket_type VARCHAR(32), ticket VARCHAR(1024), ticket_number VARCHAR(32), ticket_info VARCHAR(1024), retry INTEGER, status VARCHAR(16));".format(self.table_name))
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
        now = datetime.datetime.now()# - datetime.timedelta(hours=8)

        booking_date, diff_days = None, None
        if ticket_type == TRA:
            diff_days = self.DIFF_TRA
            booking_date = "cast(cast(ticket::json->'getin_date' as varchar) as date)"

            if now.weekday() == 4:
                diff_days += 2
            elif now.weekday() == 5:
                diff_days += 1
        elif ticket_type == THSR:
            diff_days = self.DIFF_THSR
            booking_date = "cast(cast(ticket::json->'booking_date' as varchar) as date)"

        sql = "SELECT user_id, creation_datetime, ticket, retry, id FROM {} WHERE token = '{}' AND ticket_number = '-1' AND {} BETWEEN '{}' AND '{}' AND status = '{}' AND ticket_type = '{}'".format(\
            self.table_name, channel_access_token, booking_date, now.strftime("%Y-%m-%dT00:00:00"), (now + datetime.timedelta(days=diff_days)).strftime("%Y-%m-%dT23:59:59"), status, ticket_type)

        return [(row[0], row[1], json.loads(row[2]), row[3], row[4]) for row in self.select(sql)]

    def get_status(self, user_id, ticket_type, ticket_number):
        sql = "SELECT status FROM ticket WHERE user_id = '{}' AND ticket_type = '{}' AND ticket_number = '{}'".format(user_id, ticket_type, ticket_number)

        status = None
        for row in self.select(sql):
            status = row[0]

        return status

    def set_status(self, user_id, ticket_type, status, ticket_number=None, tid=None):
        if ticket_number is not None:
            sql = "UPDATE {} SET status = '{}' WHERE user_id = '{}' and ticket_number = '{}' AND ticket_type = '{}'".format(\
                self.table_name, status, user_id, ticket_number, ticket_type)
        elif tid is not None:
            sql = "UPDATE {} SET status = '{}' WHERE user_id = '{}' and id = {} AND ticket_type = '{}'".format(\
                self.table_name, status, user_id, tid, ticket_type)
        else:
            return 0

        return self.cmd(sql)

    def memory(self, user_id, ticket_type, ticket_number):
        sql = "SELECT ticket::json->'person_id' as person_id, ticket::json->'cellphone' as phone, ticket::json->'booking_type' as booking_type FROM {} WHERE user_id = '{}' AND ticket_type = '{}' and ticket_number = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(self.table_name, user_id, ticket_type, ticket_number)

        c = 0
        param = {"person_id": None, "cellphone": None, "booking_type": None}
        for row in self.select(sql):
            param = {"person_id": row[0], "cellphone": row[1], "booking_type": row[2]}
            c = db_profile.ask(user_id, ticket_type, json.dumps(param))

        return c

    def book(self, user_id, creation_datetime, ticket_number, status, ticket_type, ticket_info):
        sql = "UPDATE {} SET ticket_number = '{}', status = '{}', ticket_info = '{}' WHERE token = '{}' AND user_id = '{}' and creation_datetime = '{}' AND ticket_type = '{}'".format(\
            self.table_name, ticket_number, status, ticket_info.replace("'", "\""), channel_access_token, user_id, creation_datetime, ticket_type)

        return self.cmd(sql)

    def retry(self, user_id, creation_datetime, ticket_type):
        sql = "UPDATE {} SET retry = retry + 1 WHERE token = '{}' AND user_id = '{}' and creation_datetime = '{}' AND ticket_type = '{}'".format(\
            self.table_name, channel_access_token, user_id, creation_datetime, ticket_type)

        return self.cmd(sql)

    def reset(self, user_id, ticket_type, tid):
        sql = "UPDATE {} SET retry = 0, status = '{}' WHERE token = '{}' AND user_id = '{}' AND ticket_type = '{}' AND id = {}".format(\
            self.table_name, TICKET_STATUS_SCHEDULED, channel_access_token, user_id, ticket_type, tid)

        return self.cmd(sql)

    def unscheduled(self, user_id, tid, status=TICKET_STATUS_UNSCHEDULED):
        sql = "UPDATE {} SET status = '{}' WHERE user_id = '{}' AND id = {}".format(self.table_name, status, user_id, tid)

        return self.cmd(sql)

    def get_person_id(self, user_id, ticket_number, ticket_type):
        sql = "SELECT ticket::json->'person_id' as uid FROM {} WHERE user_id = '{}' and ticket_number = '{}' AND ticket_type = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(\
            self.table_name, user_id, ticket_number, ticket_type)

        person_id = None
        for row in self.select(sql):
            person_id = row[0]

        return person_id

    def list_scheduled_tickets(self, user_id, ticket_type, status=TICKET_STATUS_SCHEDULED):
        sql = "SELECT id, ticket, retry FROM {} WHERE user_id = '{}' AND status = '{}' AND ticket_type = '{}' ORDER BY id DESC".format(self.table_name, user_id, status, ticket_type)

        results = []
        for row in self.select(sql):
            tid = row[0]
            ticket = json.loads(row[1])
            ticket["retry"] = str(row[2])

            results.append((tid, ticket))

        return results

    def list_booked_tickets(self, user_id, ticket_type, status=TICKET_STATUS_BOOKED):
        now = datetime.datetime.now().strftime("%Y-%m-%d")

        sql = "SELECT ticket_info, retry FROM {} WHERE user_id = '{}' AND status = '{}' AND ticket_type = '{}' AND cast(substring(cast(ticket_info::json->'搭乘時間' as varchar) from 2 for 16) as date) > '{}' ORDER BY id DESC".format(self.table_name, user_id, status, ticket_type, now)

        results = []
        for row in self.select(sql):
            ticket = json.loads(row[0])
            ticket["retry"] = str(row[1])

            results.append(ticket)

        return results

class TicketMode(Mode):
    TRA_CANCELED_URL = "http://railway.hinet.net/ccancel_rt.jsp"

    def reset_memory(self, user_id, question):
        if user_id not in self.memory or question.lower() in TICKET_CMD_RESET:
            self.new_memory(user_id)

    def cancel_tra_ticket(self, user_id, ticket_number):
        reply_txt = None

        status = self.db.get_status(user_id, TRA, ticket_number)
        if status != TICKET_STATUS_BOOKED:
            reply_txt = "此台鐵票號({})已取消".format(ticket_number)
        else:
            person_id = self.db.get_person_id(user_id, ticket_number, TRA)
            reply_txt = "取消台鐵車票({})失敗，請稍後再試或請上台鐵網站取消".format(ticket_number)

            if person_id is not None:
                f = urllib2.urlopen("{}?personId={}&orderCode={}".format(self.TRA_CANCELED_URL, person_id, ticket_number))
                content = unicode(f.read(), f.headers.getparam('charset'))
                if content.find("&#24744;&#30340;&#36554;&#31080;&#21462;&#28040;&#25104;&#21151;") > -1:
                    self.db.set_status(user_id, TRA, TICKET_STATUS_CANCELED, ticket_number)

                    reply_txt = txt_ticket_cancel(CTRA, ticket_number)

        return reply_txt

    def cancel_thsr_ticket(self, user_id, ticket_number):
        reply_txt = None

        status = self.db.get_status(user_id, THSR, ticket_number)
        if status != TICKET_STATUS_BOOKED:
            reply_txt = "此高鐵票號({})已取消".format(ticket_number)
        else:
            person_id = self.db.get_person_id(user_id, ticket_number, THSR)
            is_cancel = booking_thsr.cancel_ticket(person_id, ticket_number, driver="phantom")

            reply_txt = "取消高鐵車票({})失敗，請稍後再試或請上高鐵網站取消".format(ticket_number)
            if is_cancel:
                self.db.set_status(user_id, THSR, TICKET_STATUS_CANCELED, ticket_number)
                reply_txt = txt_ticket_cancel(CTHSR, ticket_number)

        return reply_txt

    def cancel_ticket(self, user_id, ticket_type, ticket_number):
        mode = "未知"
        if ticket_type == TRA:
            mode = CTRA
        elif ticket_type == THSR:
            mode = CTHSR

        reply_txt = "進入取消{}訂票程序".format(mode)
        if ticket_type == TRA:
            reply_txt = self.cancel_tra_ticket(user_id, ticket_number)
        elif ticket_type == THSR:
            reply_txt = self.cancel_thsr_ticket(user_id, ticket_number)
        else:
            log("Not found the ticket_type - {}".format(ticket_type))

        return reply_txt

    def is_cancel_command(self, user_id, question):
        is_cancel, reply_txt = False, None

        p = re.compile("^ticket_({})={}\+([\d]+)$".format("|".join(TYPE), TICKET_STATUS_CANCELED))
        m = p.match(question)
        if m:
            ticket_type, ticket_number = m.group(1), m.group(2)

            is_cancel = True
            reply_txt = self.cancel_ticket(user_id, ticket_type, ticket_number)

        return is_cancel, reply_txt

    def is_list_command(self, user_id, question):
        reply_txt = None

        if question in TICKET_CMD_QUERY:
            reply_txt = []
            for status in [TICKET_STATUS_SCHEDULED, TICKET_STATUS_BOOKED]:
                message = self.list_tickets(user_id, self.ticket_type, status)
                if message:
                    reply_txt.append(message)

            if not reply_txt:
                reply_txt = txt_ticket_zero()

        return reply_txt

    def is_unscheduled_command(self, user_id, question):
        reply_txt = None

        p = re.compile("^ticket_({})={}\+([\d]+)$".format("|".join(TYPE), TICKET_STATUS_UNSCHEDULED))
        m = p.match(question)
        if m:
            tid = int(m.group(2))
            count = self.db.unscheduled(user_id, tid)
            if count > 0:
                reply_txt = "成功取消預訂票 - {}".format(tid)

        return reply_txt

    def is_failed_command(self, user_id, question):
        reply_txt = None

        p = re.compile("^ticket_({})={}\+([\d]+)$".format("|".join(TYPE), TICKET_STATUS_FAILED))
        m = p.match(question)
        if m:
            ticket_type, ticket_number = m.group(1), m.group(2)
            count = self.db.set_status(user_id, ticket_type, TICKET_STATUS_FAILED, ticket_number)
            if count > 0:
                reply_txt = "標示此張車票({})為已取消".format(ticket_number)
            else:
                reply_txt = "標示失敗，請稍後再試"

        return reply_txt

    def is_memory_command(self, user_id, question):
        reply_txt = None

        p = re.compile("^ticket_({})={}\+([\d\w]+)$".format("|".join(TYPE), TICKET_STATUS_MEMORY))
        m = p.match(question)
        if m:
            ticket_type, ticket_number = m.group(1), m.group(2)

            c = self.db.memory(user_id, ticket_type, ticket_number)
            if c > 0:
                reply_txt = "已紀錄此張訂票資訊，可節省下次輸入時間"
            else:
                reply_txt = "記錄訂票人資訊失敗，請稍後再試"

        return reply_txt

    def is_retry_command(self, user_id, question):
        reply_txt = None

        p = re.compile("^ticket_({})={}\+([\d]+)$".format("|".join(TYPE), TICKET_STATUS_RETRY))
        m = p.match(question)
        if m:
            ticket_type, tid = m.group(1), m.group(2)

            c = self.db.reset(user_id, ticket_type, tid)
            if c > 0:
                reply_txt = "繼續嘗試訂購您的車票"
            else:
                reply_txt = "找不到此張預訂車票，請嘗試再訂購一張"

        return reply_txt

    def translate_ticket(self, ticket_type, ticket, id=None):
        message = None

        if ticket_type == TRA:
            message = self.translate_tra(ticket, id)
        elif ticket_type == THSR:
            message = self.translate_thsr(ticket, id)
        else:
            log("Not found this ticket type - {}".format(ticket_type))

        return message.strip()

    def translate_tra(self, ticket, id=None):
        message = None
        if id is None:
            message = "台鐵預約訂票\n===================\n"
        else:
            message = "台鐵預約訂票 - {}\n===================\n".format(id)

        for name, k in [("訂票ID", "person_id"), ("搭車日期", "getin_date"), ("搭車時間", "setime"), ("上下車站", "station"), ("車種", "train_type"), ("張數", "order_qty_str"), ("嘗試訂票次數", "retry")]:
           if k == "station":
                message += "{}: {}-{}\n".format(name, get_station_name(ticket["from_station"]), get_station_name(ticket["to_station"]))
           elif k == "train_type":
                message += "{}: {}\n".format(name, get_train_name(ticket[k]))
           elif k == "setime":
                message += "{}: {}-{}\n".format(name, ticket["getin_start_dtime"], ticket["getin_end_dtime"])
           elif ticket.get(k, None) is not None:
                message += "{}: {}\n".format(name, ticket[k].split("-")[0])

        return message

    def translate_thsr(self, ticket, id=None):
        message = None
        if id is None:
            message = "高鐵預約訂票\n================\n"
        else:
            message = "高鐵預約訂票 - {}\n================\n".format(id)

        for name, k in [("訂票ID", "person_id"), ("聯絡方式", "cellphone"), ("搭車時間", "booking_setime"), ("上下車站", "booking_station"), ("成人/小孩/學生張數", "booking_amount"), ("嘗試訂票次數", "retry")]:
            if k == "booking_setime":
                message += "{}: {} {}-{}\n".format(name, ticket["booking_date"], ticket["booking_stime"].split(":")[0], ticket["booking_etime"].split(":")[0])
            elif k == "booking_station":
                sstation = ticket["selectStartStation"]
                estation = ticket["selectDestinationStation"]

                if isinstance(sstation, unicode):
                    sstation = sstation.encode(UTF8)
                    estation = estation.encode(UTF8)

                message += "{}: {}-{}\n".format(name, sstation, estation)
            elif k == "booking_amount":
                message += "{}: ".format(name)
                for amount in ["ticketPanel:rows:0:ticketAmount", "ticketPanel:rows:1:ticketAmount", "ticketPanel:rows:4:ticketAmount"]:
                    message += "{}/".format(ticket.get(amount, 0))
                message = message.strip("/")
                message += "\n"
            elif ticket.get(k, None) is not None:
                message += "{}: {}\n".format(name, ticket[k].encode(UTF8) if isinstance(ticket[k], unicode) else ticket[k])

        return message

    def get_ticket_body(self, ticket, ticket_type, status, headers):
        body = ""
        if status == TICKET_STATUS_SCHEDULED:
            body = self.translate_ticket(ticket_type, ticket[1], ticket[0])
        elif status == TICKET_STATUS_BOOKED:
            for k in headers:
                v = ticket.get(k, None)
                if v is None:
                    v = ticket[u"起訖站"]

                if v.count(":") in [0, 2] and v.find(u"：") == -1:
                    body += "{}: {}\n".format(k.encode(UTF8), v.encode(UTF8))
                else:
                    body += "{}\n".format(v.encode(UTF8))
            body = body.strip()

        number = None
        if status == TICKET_STATUS_SCHEDULED:
            number = ticket[0]
        elif status == TICKET_STATUS_BOOKED:
            number = ticket[u"票號"]

        m = None
        if status == TICKET_STATUS_SCHEDULED:
            m = MessageTemplateAction(label=txt_ticket_continued(), text='ticket_{}={}'.format(ticket_type, TICKET_STATUS_AGAIN))
        elif status == TICKET_STATUS_BOOKED:
            m = MessageTemplateAction(label=txt_ticket_failed(), text='ticket_{}={}+{}'.format(ticket_type, TICKET_STATUS_FAILED, number))

        return number, body, m

    def list_tickets(self, user_id, ticket_type, status):
        text_cancel_label, text_cancel_text, tickets = None, None, []
        if status == TICKET_STATUS_SCHEDULED:
            tickets = self.db.list_scheduled_tickets(user_id, ticket_type)
            text_cancel_label = "取消預訂票"
            text_cancel_text = TICKET_STATUS_UNSCHEDULED
        elif status == TICKET_STATUS_BOOKED:
            tickets = self.db.list_booked_tickets(user_id, ticket_type)
            text_cancel_label = txt_ticket_cancel()
            text_cancel_text = TICKET_STATUS_CANCELED

        headers = TICKET_HEADERS_BOOKED_TRA if ticket_type == TRA else TICKET_HEADERS_BOOKED_THSR

        reply_txt = None
        if len(tickets) == 1:
            ticket = tickets[0]

            number, body, m = self.get_ticket_body(ticket, ticket_type, status, headers)
            messages = [MessageTemplateAction(label=text_cancel_label, text='ticket_{}={}+{}'.format(ticket_type, text_cancel_text, number)), m]

            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=ConfirmTemplate(text=body, actions=messages))
        elif len(tickets) > 1:
            messages = []
            for ticket in tickets:
                number, body, m = self.get_ticket_body(ticket, ticket_type, status, headers)
                message = CarouselColumn(text=body, actions=[MessageTemplateAction(label=text_cancel_label, text='ticket_{}={}+{}'.format(ticket_type, text_cancel_text, number)), m])

                messages.append(message)

            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=CarouselTemplate(columns=messages))

        return reply_txt

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = None
        self.reset_memory(user_id, question)

        reply_txt = self.is_list_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        reply_txt = self.is_memory_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        reply_txt = self.is_failed_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        reply_txt = self.is_unscheduled_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        reply_txt = self.is_retry_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        return self.conversion_process(question, user_id, user_name)

    def conversion_process(self, question, user_id=None, user_name=None):
        raise NotImplementedError

class TRATicketMode(TicketMode):
    def init(self):
        self.memory = {}
        self.db = TicketDB()
        self.ticket_type = TRA

    def conversion_process(self, question, user_id=None, user_name=None):
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
                    self.memory[user_id]["getin_end_dtime"] = "{:02d}:00".format(question)
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

        for row in db_profile.get_profile(user_id, self.ticket_type):
            for k, v in json.loads(row[0]).items():
                if k in self.memory[user_id] and v is not None and v.lower() not in ["none", "null"]:
                    self.memory[user_id][k] = v

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
        self.ticket_type = THSR

    def conversion_process(self, question, user_id=None, user_name=None):
        is_cancel, reply_txt = self.is_cancel_command(user_id, question)
        if not is_cancel:
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
                message = self.translate_ticket(self.ticket_type, elf.memory[user_id])

                if question not in ["ticket_{}={}".format(self.ticket_type, TICKET_STATUS_CONFIRM), "ticket_{}={}".format(self.ticket_type, TICKET_STATUS_AGAIN)]:
                    template = ConfirmTemplate(text=message, actions=[
                        MessageTemplateAction(label=txt_ticket_confirm(), text='ticket_{}={}'.format(self.ticket_type, TICKET_STATUS_CONFIRM)),
                        MessageTemplateAction(label=txt_ticket_cancel(), text='ticket_{}={}'.format(self.ticket_type, TICKET_STATUS_AGAIN)),
                    ])

                    reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=template)
                else:
                    if question == "ticket_{}={}".format(self.ticket_type, TICKET_STATUS_CONFIRM):
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

mode_tra_ticket = TRATicketMode(MODE_TRA_TICKET)
mode_thsr_ticket = THSRTicketMode(MODE_THSR_TICKET)

if __name__ == "__main__":
    person_id = "L122760167"
    user_id = "Ua5f08ec211716ba22bef87a8ac2ca6ee"
    creation_datetime = "2017-02-20 07:57:04"
    #question = "ticket_tra=memory+738148"
    #question = "ticket_thsr=memory+07123684"
    question = "ticket_thsr=retry+171"
    print mode_thsr_ticket.conversion(question, user_id)

    '''
    questions = [person_id, "2017/03/06", "10-22", "台南", "花蓮", "1", "全部車種", "ticket_tra=confirm"]
    for question in questions:
        message = mode_tra_ticket.conversion(question, user_id)
        if isinstance(message, str):
            print message
        elif isinstance(message, list):
            for m in message:
                print m
        else:
            print message.as_json_string()

    questions = ["booking_type=general", person_id, "0921747196", "2017/03/06", "17", "23", "左營", "南港", "1", "0", "ticket_thsr=confirm"]
    for question in questions:
        message = mode_thsr_ticket.conversion(question, user_id)
        if isinstance(message, str):
            print message
        elif isinstance(message, list):
            for m in message:
                print m
        elif message is not None:
            print message.as_json_string()
    '''
