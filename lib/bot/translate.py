# -*- coding: utf-8 -*-

import os
import re
import sys

from googleapiclient.discovery import build

import logging
logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)

from lib.common.utils import UTF8
from lib.common.bot import Bot

class TranslateBot(Bot):
    def set_dataset(self):
        key = os.environ["GOOGLE_TRANSLATE_KEY"]
        self.service = build('translate', 'v2', developerKey=key)

    def crawl_job(self, is_gen=True):
        pass

    def gen_results(self):
        pass

    def bots(self, question, source="en", target="zh-TW"):
        answer = None
        try:
            question.decode("ascii")

            answer = []
            for v in (self.service.translations().list(source=source, target=target, q=re.split("\s+", question)).execute()).values():
                for sub_v in v:
                    answer.append(sub_v["translatedText"])

            answer = " ".join(answer).encode(UTF8)
        except UnicodeDecodeError:
            pass

        return answer

bot = TranslateBot()

if __name__ == "__main__":
    bot.init()

    print bot.bots(sys.argv[1])
