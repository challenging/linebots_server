# -*- coding: utf-8 -*-

import sys
import googlemaps

from datetime import datetime

from lib.common.utils import UTF8
from lib.common.bot import Bot

class PlaceBot(Bot):
    def set_dataset(self):
        self.client = googlemaps.Client(key='AIzaSyCDazDbJvbM1YDgXCP3C1CPqXOrHZDGKfw')

    def crawl_job(self, is_gen=True):
        pass

    def gen_results(self):
        pass

    def bots(self, location, msg, lang="zh_TW"):
        rc = self.client.places_nearby(keyword=msg, location=location, language=lang, open_now=True, rank_by='distance', type=msg)

        return rc


bot = PlaceBot()

if __name__ == "__main__":
    bot.init()

    location = (25.04184, 121.55265)

    for results in bot.bots(location, sys.argv[1])["results"]:
        for k, v in results.items():
            print k, v

        print
