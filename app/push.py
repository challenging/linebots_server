# -*- coding: utf-8 -*-

import os
import time
import click
import random
import threading

from lib.common.utils import log, channel_access_token
from lib.common.message import txt_ticket_cancel

from lib.mode.ticket import CTRA, TRA, THSR, mode_tra_ticket
from lib.ticket.utils import TICKET_STATUS_CANCEL, TRAUtils
from lib.push.linebots import booking_tra_ticket, booking_thsr_ticket

from linebot.models import TextSendMessage
from linebot import LineBotApi
line_bot_api = LineBotApi(channel_access_token)

class BookingThread(threading.Thread):
    def init(self, booking):
        self.booking = booking

    def run(self):
        while True:
            self.booking("chrome")
            time.sleep(random.randint(10, 20))

class TRACancelThread(threading.Thread):
    def run(self):
        global line_bot_api

        while True:
            for user_id, ticket_number, person_id in mode_tra_ticket.db.get_tickets_by_status(TICKET_STATUS_CANCEL, TRA):
                if TRAUtils.is_canceled(person_id, ticket_number):
                    mode_tra_ticket.db.set_status(user_id, TRA, TICKET_STATUS_CANCELED, ticket_number)

                    print user_id, ticket_number
                    print txt_ticket_cancel(CTRA, ticket_number)
                    line_bot_api.push_message(user_id, TextSendMessage(text=txt_ticket_cancel(CTRA, ticket_number)))

            time.sleep(10)

@click.command()
def run():
    driver = "chrome"

    t = TRACancelThread()
    t.start()

    while True:
        booking_tra_ticket(driver)
        booking_thsr_ticket(driver)

        time.sleep(random.randint(10, 20))

    t.join()

if __name__ == "__main__":
    run()
