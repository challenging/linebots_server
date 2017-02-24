#!/usr/bin/env python

import time
import click
import threading

from lib.common.utils import log
from lib.bot import fxrate, weather, lucky, bus

class BotThread(threading.Thread):
    def init_bot(self, bot):
        self.bot_name = bot
        if self.bot_name == "weahter":
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

@click.command()
def main():
    fxrate.bot.init()
    weather.bot.init()
    lucky.bot.init()
    bus.bot.init()
    bus.bot.hourly_job()

    threads = []
    for bot_name, sleeping in zip(["weather", "fxrate", "lucky", "bus"], [900, 60, 3600, 40]):
        thread = BotThead()
        thread.init_bot(bot_name)
        thread.set_sleeping(sleeping)

        thread.start()

        threads.append(thread)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
