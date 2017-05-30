#!/usr/bin/env python

import time
import click
import threading
import datetime

from lib.mode.ticket.ticket import TRA, THSR
from lib.mode.ticket.tra import TRA
from lib.mode.ticket.thsr import THSR

from lib.ticket.utils import TICKET_STATUS_BOOKED, TICKET_STATUS_PAY, TICKET_STATUS_CANCELED, TICKET_STATUS_RETRY, TRAUtils
from lib.common.utils import log

from lib.crawler.tra_crawler import TRACrawler
from lib.bot import fxrate, weather, lucky, bus


class BotThread(threading.Thread):
    def init_bot(self, bot):
        self.bot_name = bot
        if self.bot_name == "weather":
            self.bot = weather.bot
        elif self.bot_name == "fxrate":
            self.bot = fxrate.bot
        elif self.bot_name == "lucky":
            self.bot = lucky.bot
        elif self.bot_name == "bus":
            self.bot = bus.bot
        else:
            log("Not found this bot name - {}".format(self.bot_name))
            raise NotImplementedError

        self.bot.init()
        if self.bot == "bus":
            self.bot.hourly_job()
            self.hourly_crawling = True

    def set_sleeping(self, sleeping):
        self.sleeping = sleeping

    def run(self):
        while True:
            try:
                self.bot.crawl_job()

                if self.bot_name == "bus" and self.hourly_crawling and datetime.datetime.now().hour%6 == 1:
                    self.bot.hourly_job()
                    self.hourly_crawling = False
                else:
                    self.hourly_crawling = True
            except Exception as e:
                self.init_bot(self.bot_name)

                log(e)

            time.sleep(self.sleeping)

class CrawlerThread(threading.Thread):
    def init_bot(self, mode):
        if mode == TRA:
            self.crawler = TRACrawler()
        else:
            raise NotImplementedError

    def set_sleeping(self, sleeping):
        self.sleeping = sleeping

    def run(self):
        while True:
            try:
                self.crawler.run()
            except Exception as e:
                log(e)

            time.sleep(self.sleeping)

class TicketThread(threading.Thread):
    def init_bot(self, mode):
        if mode == TRA:
            self.ticket = mode_tra_ticket
        elif mode == THSR:
            self.ticket = mode_thsr_ticket
        else:
            raise NotImplementedError

    def set_sleeping(self, sleeping):
        self.sleeping = sleeping

    def run(self):
        while True:
            try:
                now = datetime.datetime.now()
                if (now.hour == 22 and now.minute >= 30 and now.minute <= 55) or (now.hour == 23 and now.minute >= 0 and now.minute <= 5):
                    for row in self.ticket.db.check_booking(self.ticket.ticket_type, TICKET_STATUS_RETRY):
                        user_id, ticket_number, person_id, tid = row

                        self.ticket.db.reset(user_id, self.ticket.ticket_type, tid)
                        log("reset the ticket({}) of {} for {}".format(tid, self.ticket.ticket_type, user_id))

                for row in self.ticket.db.check_booking(self.ticket.ticket_type, TICKET_STATUS_BOOKED):
                    user_id, ticket_number, person_id, tid = row

                    status = TRAUtils.get_status(person_id, ticket_number)
                    if status in [TICKET_STATUS_PAY, TICKET_STATUS_CANCELED]:
                        self.ticket.db.modify_status(user_id, tid, status)
            except Exception as e:
                log(e)

            time.sleep(self.sleeping)

@click.command()
def main():
    threads = []

    fxrate.bot.init()
    weather.bot.init()
    lucky.bot.init()
    bus.bot.init()
    bus.bot.hourly_job()

    #for bot_name, sleeping in zip(["weather", "fxrate", "lucky", "bus"], [900, 60, 3600, 40]):
    for bot_name, sleeping in zip(["weather", "fxrate", "lucky"], [900, 60, 3600]):
        thread = BotThread()
        thread.init_bot(bot_name)
        thread.set_sleeping(sleeping)

        thread.start()

        threads.append(thread)

    for mode, sleeping in zip([TRA], [60]):
        thread = TicketThread()
        thread.init_bot(mode)
        thread.set_sleeping(sleeping)

        thread.start()
        threads.append(thread)

    for crawler_name, sleeping in zip([TRA], [60*60*12]):
        thread = CrawlerThread()
        thread.init_bot(crawler_name)
        thread.set_sleeping(sleeping)

        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
