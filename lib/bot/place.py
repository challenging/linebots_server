# -*- coding: utf-8 -*-

import os
import sys
import googlemaps

from datetime import datetime

from lib.common.utils import UTF8, read_cfg
from lib.common.bot import Bot

class PlaceBot(Bot):
    def set_dataset(self):
        self.key = os.environ["GOOGLE_MAP_KEY"]

        self.client = googlemaps.Client(key=self.key)
        self.config_parser = read_cfg(os.path.abspath(__file__).replace(".py", ".cfg"))

    def crawl_job(self, is_gen=True):
        pass

    def gen_results(self):
        pass

    def bots(self, location, msg, section="mapping", lang="zh_TW"):
        type = None

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
            for results in r["results"]:
                rc = {}
                rc["name"] = results["name"]
                rc["location"] = (results["geometry"]["location"]["lat"], results["geometry"]["location"]["lng"])
                rc["address"] = results["vicinity"]
                rc["photo_url"] = "https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={}&key={}".format(results["photos"][0]["photo_reference"], self.key)

                places.append(rc)

        return places

bot = PlaceBot()

if __name__ == "__main__":
    bot.init()

    location = (25.04184, 121.55265)

    for results in bot.bots(location, sys.argv[1]):
        print results
        print
