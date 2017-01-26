# -*- coding: utf-8 -*-

import os
import sys
import googlemaps

from datetime import datetime

from lib.common.utils import UTF8, read_cfg
from lib.common.bot import Bot
from lib.bot import google_search

class PlaceBot(Bot):
    def set_dataset(self):
        self.key = os.environ["GOOGLE_MAP_KEY"]

        self.client = googlemaps.Client(key=self.key)
        self.config_parser = read_cfg(os.path.abspath(__file__).replace(".py", ".cfg"))

    def crawl_job(self, is_gen=True):
        pass

    def gen_results(self):
        pass

    def bots(self, given, section="mapping", lang="zh_TW"):
        type = None
        location, msg = given

        try:
            msg.encode('ascii')

            type = msg
        except UnicodeDecodeError:
            print msg, self.config_parser.has_option("mapping", msg)
            if self.config_parser.has_option("mapping", msg):
                type = self.config_parser.get("mapping", msg)

        places = []
        if type is not None:
            r = self.client.places_nearby(keyword=type, location=location, language=lang, open_now=True, rank_by='distance', type=type)
            for idx, results in enumerate(r["results"]):
                message = {}

                if "phtots" in results:
                    message["image"] = "https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={}&key={}".format(results["photos"][0]["photo_reference"], self.key)
                else:
                    message["image"] = results["icon"]

                message["name"] = results["name"]
                message["address"] = results["vicinity"]
                message["location"] = (results["geometry"]["location"]["lat"], results["geometry"]["location"]["lng"])

                uri = google_search.bot.bots(message["name"].encode(UTF8))
                message["uri"] = uri if uri else "http://tw.yahoo.com"
                places.append(message)

                if idx > 1:
                    break

        return places

bot = PlaceBot()

if __name__ == "__main__":
    bot.init()

    location = (25.04184, 121.55265)

    for results in bot.bots((location, sys.argv[1])):
        print results
        print
