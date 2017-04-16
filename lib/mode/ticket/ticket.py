#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import time
import datetime

from linebot.models import (
    ConfirmTemplate, MessageTemplateAction, TemplateSendMessage, ButtonsTemplate, CarouselTemplate, CarouselColumn
)

from lib.common.mode import Mode
from lib.common.db import DB
from lib.db.profile import db_profile
from lib.ticket import booking_thsr

from lib.common.utils import channel_access_token, log, UTF8

from lib.common.message import (
    txt_ticket_memory, txt_ticket_cancel, txt_ticket_zero, txt_ticket_continued, txt_ticket_failed, txt_ticket_paid, txt_not_support, txt_ticket_retry,
    txt_ticket_split, txt_ticket_split_body,
)

from lib.ticket.utils import (
    tra_stations, get_station_name, get_train_name, TRAUtils,
    TICKET_COUNT, TICKET_CMD_QUERY, TICKET_CMD_RESET, TICKET_HEADERS_BOOKED_TRA, TICKET_HEADERS_BOOKED_THSR, TICKET_RETRY, TICKET_STATUS_PAY,
    TICKET_STATUS_BOOKED, TICKET_STATUS_CANCELED, TICKET_STATUS_SCHEDULED, TICKET_STATUS_UNSCHEDULED, TICKET_STATUS_MEMORY, TICKET_STATUS_CANCEL,
    TICKET_STATUS_FORGET, TICKET_STATUS_AGAIN, TICKET_STATUS_FAILED, TICKET_STATUS_CONFIRM, TICKET_STATUS_RETRY, TICKET_STATUS_SPLIT, TICKET_STATUS_TRANSFER,
    TICKET_STATUS_WAITTING,
)

TRA = "tra"
THSR = "thsr"
CTRA = "台鐵"
CTHSR = "高鐵"

TYPE = [TRA, THSR]


class TicketDB(DB):
    table_name = "ticket"

    DIFF_TRA = 14
    DIFF_THSR = 27

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (id SERIAL, token VARCHAR(256), user_id VARCHAR(128), creation_datetime TIMESTAMP, ticket_type VARCHAR(32), ticket VARCHAR(1024), ticket_number VARCHAR(32), ticket_info VARCHAR(1024), retry INTEGER, status VARCHAR(16), parent_id INTEGER, note VARCHAR(512));".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx_1 ON {table_name} (token, ticket_type, creation_datetime, ticket_number);".format(table_name=self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx_2 ON {table_name} (token, user_id, ticket_type, ticket_number);".format(table_name=self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx_3 ON {table_name} (id);".format(table_name=self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx_4 ON {table_name} (ticket_type, status);".format(table_name=self.table_name))
        cursor.close()

    def get_ticket(self, user_id, ticket_type, tid):
        sql = "SELECT ticket FROM {} WHERE user_id = '{}' AND ticket_type = '{}' and id = '{}'".format(self.table_name, user_id, ticket_type, tid)

        return [json.loads(row[0]) for row in self.select(sql)]

    def ask(self, user_id, ticket, ticket_type):
        cursor = self.conn.cursor()

        count_select = 0
        sql = "SELECT COUNT(1) FROM {} WHERE ticket_type = '{}' AND status = 'scheduled' AND user_id = '{}'".format(self.table_name, ticket_type, user_id)
        cursor.execute(sql)
        for row in cursor.fetchall():
            count_select = row[0]

        count_insert = 0
        if count_select < TICKET_COUNT:
            sql = "INSERT INTO {}(token, user_id, creation_datetime, ticket_type, ticket, ticket_number, retry, status) VALUES('{}', '{}', '{}', '{}', '{}', '-1', 0, '{}');".format(\
                self.table_name, channel_access_token, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, ticket, TICKET_STATUS_SCHEDULED)
            cursor.execute(sql)
            count_insert = cursor.rowcount

        cursor.close()

        return count_select, count_insert

    def non_booking(self, ticket_type, status=TICKET_STATUS_SCHEDULED):
        now = datetime.datetime.now()

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

    def check_booking(self, ticket_type, status=TICKET_STATUS_BOOKED):
        now = datetime.datetime.now()

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

        sql = "SELECT user_id, ticket_number, ticket::json-> 'person_id', id FROM {} WHERE {} BETWEEN '{}' AND '{}' AND status = '{}' AND ticket_type = '{}'".format(\
            self.table_name, booking_date, now.strftime("%Y-%m-%dT00:00:00"), (now + datetime.timedelta(days=diff_days)).strftime("%Y-%m-%dT23:59:59"), status, ticket_type)

        return [(row[0], row[1], row[2], row[3]) for row in self.select(sql)]

    def get_tickets_by_status(self, status, ticket_type):
        sql = "SELECT user_id, id, ticket_number, ticket::json->'person_id' FROM {} WHERE token = '{}' AND status = '{}' AND ticket_type = '{}'".format(\
            self.table_name, channel_access_token, status, ticket_type)

        for row in self.select(sql):
            yield (row[0], row[1], row[2], row[3])

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
        sql = "UPDATE {} SET ticket_number = '{}', status = '{}', ticket_info = '{}' WHERE user_id = '{}' and creation_datetime = '{}' AND ticket_type = '{}'".format(\
            self.table_name, ticket_number, status, ticket_info.replace("'", "\""), user_id, creation_datetime, ticket_type)

        return self.cmd(sql)

    def retry(self, user_id, creation_datetime, ticket_type):
        sql = "UPDATE {} SET retry = retry + 1 WHERE user_id = '{}' and creation_datetime = '{}' AND ticket_type = '{}'".format(\
            self.table_name, user_id, creation_datetime, ticket_type)

        return self.cmd(sql)

    def reset(self, user_id, ticket_type, tid):
        sql = "UPDATE {} SET retry = 0, status = '{}' WHERE user_id = '{}' AND ticket_type = '{}' AND id = {}".format(\
            self.table_name, TICKET_STATUS_SCHEDULED, user_id, ticket_type, tid)

        return self.cmd(sql)

    def transfer(self, user_id, ticket_type, tid, transfer_station_id):
        ticket = self.get_ticket(user_id, ticket_type, tid)[0]
        to_station = ticket["to_station"]
        ticket["to_station"] = transfer_station_id

        c = self.modify_status(user_id, tid, TICKET_STATUS_SPLIT)

        if c > 0:
            sql = "INSERT INTO {}(token, user_id, creation_datetime, ticket_type, ticket, ticket_number, retry, status, parent_id, note) VALUES('{}', '{}', '{}', '{}', '{}', '-1', 0, '{}', '{}', '{}');".\
                    format(self.table_name, channel_access_token, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, json.dumps(ticket), TICKET_STATUS_SCHEDULED, tid, to_station)
            c = self.cmd(sql)

            if c > 0:
                ticket["from_station"] = transfer_station_id
                ticket["to_station"] = to_station
                sql = "INSERT INTO {}(token, user_id, creation_datetime, ticket_type, ticket, ticket_number, retry, status, parent_id, note) VALUES('{}', '{}', '{}', '{}', '{}', '-1', 0, '{}', '{}', '{}');".\
                    format(self.table_name, channel_access_token, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, json.dumps(ticket), TICKET_STATUS_WAITTING, tid, to_station)
                c = self.cmd(sql)

        return c

    def modify_status(self, user_id, tid, status):
        sql = "UPDATE {} SET status = '{}' WHERE user_id = '{}' AND id = {}".format(self.table_name, status, user_id, tid)

        return self.cmd(sql)

    def prepare_cancel_ticket(self, user_id, ticket_number, ticket_type, status=TICKET_STATUS_CANCEL):
        sql = "UPDATE {} SET status = '{}' WHERE user_id = '{}' AND ticket_number = '{}' AND ticket_type = '{}'".format(self.table_name, status, user_id, ticket_number, ticket_type)

        return self.cmd(sql)

    def get_person_id(self, user_id, ticket_number, ticket_type):
        sql = "SELECT ticket::json->'person_id' as uid FROM {} WHERE user_id = '{}' and ticket_number = '{}' AND ticket_type = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(\
            self.table_name, user_id, ticket_number, ticket_type)

        person_id = None
        for row in self.select(sql):
            person_id = row[0]

        return person_id

    def list_scheduled_tickets(self, user_id, ticket_type, status=[TICKET_STATUS_SCHEDULED]):
        sql = "SELECT id, ticket, retry, parent_id FROM {} WHERE user_id = '{}' AND status IN ('{}') AND ticket_type = '{}' ORDER BY id DESC".format(\
            self.table_name, user_id, "','".join(status), ticket_type)

        results = []
        for row in self.select(sql):
            tid = row[0]
            ticket = json.loads(row[1])
            ticket["retry"] = str(row[2])
            ticket["parent_id"] = row[3]

            results.append((tid, ticket))

        return results

    def list_booked_tickets(self, user_id, ticket_type, status=TICKET_STATUS_BOOKED):
        now = datetime.datetime.now().strftime("%Y-%m-%d")

        sql = "SELECT id, ticket_info, retry, status FROM {} WHERE user_id = '{}' AND status IN ('{}') AND ticket_type = '{}' AND cast(substring(cast(ticket_info::json->'搭乘時間' as varchar) from 2 for 16) as date) > '{}' ORDER BY id DESC".format(self.table_name, user_id, "','".join(status), ticket_type, now)

        results = []
        for row in self.select(sql):
            ticket = json.loads(row[1])
            ticket[u"懶人ID"] = str(row[0])
            ticket["retry"] = str(row[2])
            ticket["status"] = row[3]

            results.append(ticket)

        return results

class TicketMode(Mode):
    DELAY_HOUR = 1

    def set_memory(self, user_id, k, v):
        self.memory[user_id][k] = v

        return True

    def reset_memory(self, user_id, question):
        if user_id not in self.memory or question.lower() in TICKET_CMD_RESET:
            self.new_memory(user_id)

    def cancel_tra_ticket(self, user_id, ticket_number):
        reply_txt = None

        status = self.db.get_status(user_id, TRA, ticket_number)
        if status != TICKET_STATUS_BOOKED:
            reply_txt = "此台鐵票號({})已取消".format(ticket_number)
        else:
            count = self.db.prepare_cancel_ticket(user_id, ticket_number, TRA)

            if count > 0:
                reply_txt = "懶人RC為您取消此張台鐵車票({})，成功後便立即通知".format(ticket_number)
            else:
                reply_txt = "懶人RC發生錯誤，請稍後再試"

        return reply_txt

    def cancel_thsr_ticket(self, user_id, ticket_number):
        reply_txt = None

        status = self.db.get_status(user_id, THSR, ticket_number)
        if status != TICKET_STATUS_BOOKED:
            reply_txt = "此高鐵票號({})已取消".format(ticket_number)
        else:
            person_id = self.db.get_person_id(user_id, ticket_number, THSR)
            is_cancel = booking_thsr.cancel_ticket(person_id, ticket_number)

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

    def is_help_command(self, user_id, question):
        reply_txt = None
        if re.search("^(help|幫助|指引)$", question.lower()):
            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(
                    title="請選擇下列選單",
                    text="Please click one of the following services",
                    actions=[MessageTemplateAction(label=txt_ticket_forget(), text="ticket_{}={}".format(self.ticket_type, TICKET_STATUS_FORGET)),
                             MessageTemplateAction(label="開始訂票", text="開始訂票"),
                             MessageTemplateAction(label="查詢訂票", text="查詢")]
                ))
        elif re.search("^ticket_({})={}$".format("|".join(TYPE), TICKET_STATUS_FORGET), question):
            m = re.match("^ticket_({})={}$".format("|".join(TYPE), TICKET_STATUS_FORGET), question)
            ticket_type = m.group(1)

            c = db_profile.ask(user_id, ticket_type, {})
            if c > 0:
                reply_txt = "成功忘記個人訂票資訊，下次訂票時會需要再輸入一次。"
            else:
                reply_txt = "忘記個人訂票資訊失敗，請稍後再試！"

        return reply_txt

    def is_cancel_command(self, user_id, question):
        reply_txt = None

        p = re.compile("^ticket_({})={}\+([\d]+)$".format("|".join(TYPE), TICKET_STATUS_CANCELED))
        m = p.match(question)
        if m:
            ticket_type, ticket_number = m.group(1), m.group(2)
            reply_txt = self.cancel_ticket(user_id, ticket_type, ticket_number)

        return reply_txt

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
            count = self.db.modify_status(user_id, tid, TICKET_STATUS_UNSCHEDULED)
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

    def is_split_command(self, user_id, question):
        reply_txt = None

        p = re.compile("^ticket_({})={}\+([\d]+)$".format("|".join(TYPE), TICKET_STATUS_SPLIT))
        m = p.match(question)
        if m:
            ticket_type, tid = m.group(1), m.group(2)
            ticket = self.db.get_ticket(user_id, ticket_type, tid)[0]
            transfer_stations = TRAUtils.get_transfer_stations(int(ticket["from_station"]), int(ticket["to_station"]))

            messages = []
            for station in transfer_stations[:5]:
                messages.append(MessageTemplateAction(label=station, text='ticket_{}={}+{}+{}'.format(ticket_type, TICKET_STATUS_TRANSFER, tra_stations[station], tid)))

            if messages:
                reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(text=txt_ticket_split_body(), actions=messages))

        return reply_txt

    def is_transfer_command(self, user_id, question):
        reply_txt = None

        p = re.compile("^ticket_({})={}\+([\d]+)\+([\d]+)$".format("|".join(TYPE), TICKET_STATUS_TRANSFER))
        m = p.match(question)
        if m:
            ticket_type, transfer_station_id, tid = m.group(1), m.group(2), m.group(3)
            c = self.db.transfer(user_id, ticket_type, tid, transfer_station_id)
            if c > 0:
                reply_txt = "這張票(懶人ID: {})將會被拆為兩張票，並以{}為中間站".format(tid, get_station_name(transfer_station_id))
            else:
                reply_txt = "拆票作業失敗，請稍後再試"

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

        if ticket.get("train_no", None) is None:
            for name, k in [("訂票ID", "person_id"), ("搭車日期", "getin_date"), ("搭車時間", "setime"), ("起迄站", "station"), ("嘗試訂票次數", "retry")]:
                if k == "station":
                    message += "{}: {}-{}, {}張\n".format(name, get_station_name(ticket["from_station"]), get_station_name(ticket["to_station"]), ticket["order_qty_str"])
                elif k == "setime":
                    message += "{}: {}-{}, {}\n".format(name, ticket["getin_start_dtime"], ticket["getin_end_dtime"],  get_train_name(ticket["train_type"]))
                elif ticket.get(k, None) is not None:
                    message += "{}: {}\n".format(name, ticket[k].split("-")[0])
                else:
                    pass
        else:
            for name, k in [("訂票ID", "person_id"), ("搭車日期", "getin_date"), ("搭車車次", "train_no"), ("起迄站", "station"), ("嘗試訂票次數", "retry")]:
                if k == "station":
                    message += "{}: {}-{}, {}張\n".format(name, get_station_name(ticket["from_station"]), get_station_name(ticket["to_station"]), ticket["order_qty_str"])
                elif ticket.get(k, None) is not None:
                    message += "{}: {}\n".format(name, ticket[k].split("-")[0])
                else:
                    pass

        return message

    def translate_thsr(self, ticket, id=None):
        message = None
        if id is None:
            message = "高鐵預約訂票\n================\n"
        else:
            message = "高鐵預約訂票 - {}\n================\n".format(id)

        for name, k in [("訂票ID", "person_id"), ("搭車時間", "booking_setime"), ("起迄站", "booking_station"), ("成人/小孩/學生張數", "booking_amount"), ("嘗試訂票次數", "retry")]:
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
            elif k == "person_id":
                message += "{}: {}, {}\n".format(name, ticket[k], ticket["cellphone"])
            elif ticket.get(k, None) is not None:
                message += "{}: {}\n".format(name, ticket[k].encode(UTF8) if isinstance(ticket[k], unicode) else ticket[k])

        return message

    def get_ticket_body(self, ticket, ticket_type, status, headers):
        global TRA

        body, number, messages = [], None, []
        if status == TICKET_STATUS_SCHEDULED:
            body = self.translate_ticket(ticket_type, ticket[1], ticket[0])
            number = ticket[0]

            retry = int(ticket[1].get("retry", 0))

            if retry >= TICKET_RETRY:
                messages.append(MessageTemplateAction(label=txt_ticket_retry(), text='ticket_{}={}+{}'.format(ticket_type, TICKET_STATUS_RETRY, number)))
                if ticket_type == TRA and ticket[1].get("parent_id", None) is None:
                    sstation, estation = int(ticket[1]["from_station"]), int(ticket[1]["to_station"])

                    transfer_stations = TRAUtils.get_transfer_stations(sstation, estation)
                    if len(transfer_stations) > 0:
                        messages.append(MessageTemplateAction(label=txt_ticket_split(), text='ticket_{}={}+{}'.format(ticket_type, TICKET_STATUS_SPLIT, number)))
            else:
                messages.append(MessageTemplateAction(label=txt_ticket_continued(), text='ticket_{}={}'.format(ticket_type, TICKET_STATUS_AGAIN)))
        elif status == TICKET_STATUS_BOOKED:
            s = ticket["status"]

            for k in headers:
                v = ticket.get(k, None)
                if v is None:
                    v = ticket[u"起迄站"]

                if v.count(":") in [0, 2] and v.find(u"：") == -1:
                    body.append("{}: {}".format(k.encode(UTF8), v.encode(UTF8)))
                else:
                    body.append(v.encode(UTF8))

            if s == TICKET_STATUS_PAY:
                body[-1] = txt_ticket_paid()
            body = "\n".join(body)

            number = ticket[u"票號"]
            messages.append(MessageTemplateAction(label=txt_ticket_memory(), text='ticket_{}={}+{}'.format(ticket_type, TICKET_STATUS_MEMORY, number)))
        elif status == TICKET_STATUS_WAITTING:
            body = self.translate_ticket(ticket_type, ticket[1], ticket[0])
            number = ticket[0]
        else:
            log("Not found this ticket type - {}".format(ticket_type))

        return number, body, messages

    def list_tickets(self, user_id, ticket_type, status):
        text_cancel_label, text_cancel_text, tickets = None, None, []
        if status == TICKET_STATUS_SCHEDULED:
            tickets = self.db.list_scheduled_tickets(user_id, ticket_type, [TICKET_STATUS_SCHEDULED, TICKET_STATUS_RETRY, TICKET_STATUS_WAITTING])
            text_cancel_label = txt_ticket_cancel(None, None, True)
            text_cancel_text = TICKET_STATUS_UNSCHEDULED
        elif status == TICKET_STATUS_BOOKED:
            tickets = self.db.list_booked_tickets(user_id, ticket_type, [TICKET_STATUS_BOOKED, TICKET_STATUS_PAY])
            text_cancel_label = txt_ticket_cancel()
            text_cancel_text = TICKET_STATUS_CANCELED

        headers = TICKET_HEADERS_BOOKED_TRA if ticket_type == TRA else TICKET_HEADERS_BOOKED_THSR

        reply_txt = None
        if len(tickets) == 1:
            ticket = tickets[0]

            messages = []
            number, body, m = self.get_ticket_body(ticket, ticket_type, status, headers)
            if status == TICKET_STATUS_BOOKED and ticket["status"] == TICKET_STATUS_PAY:
                pass
            else:
                messages = [MessageTemplateAction(label=text_cancel_label, text='ticket_{}={}+{}'.format(ticket_type, text_cancel_text, number))]

            messages.extend(m)

            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=ButtonsTemplate(text=body, actions=messages))
        else:
            messages = []
            for ticket in tickets:
                number, body, m = self.get_ticket_body(ticket, ticket_type, status, headers)

                message = []
                if status == TICKET_STATUS_BOOKED and ticket["status"] == TICKET_STATUS_PAY:
                    message.append(MessageTemplateAction(label=txt_ticket_continued(), text='ticket_{}={}'.format(ticket_type, TICKET_STATUS_AGAIN)))
                else:
                    message.append(MessageTemplateAction(label=text_cancel_label, text='ticket_{}={}+{}'.format(ticket_type, text_cancel_text, number)))

                message.extend(m)
                messages.append(CarouselColumn(text=body, actions=message))

            reply_txt = TemplateSendMessage(alt_text=txt_not_support(), template=CarouselTemplate(columns=messages))

        return reply_txt

    def conversion(self, question, user_id=None, user_name=None):
        reply_txt = self.is_help_command(user_id, question)
        if reply_txt is not None:
            return reply_txt

        self.reset_memory(user_id, question)

        for func in [self.is_list_command, self.is_memory_command, self.is_failed_command, self.is_unscheduled_command, self.is_retry_command,
                     self.is_cancel_command, self.is_split_command, self.is_transfer_command]:
            reply_txt = func(user_id, question)
            if reply_txt is not None:
                return reply_txt

        return self.conversion_process(question, user_id, user_name)

    def conversion_process(self, question, user_id=None, user_name=None):
        raise NotImplementedError
