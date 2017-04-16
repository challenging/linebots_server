#!/usr/bin/env python

import os
import datetime
import zipfile

from lib.common.crawler import Crawler

class TRACrawler(Crawler):
    def __init__(self):
        super(TRACrawler, self).__init__("http://163.29.3.98/json", os.path.join(os.path.dirname(__file__), "..", "..", "etc", "captcha", "tra"))

    def pre_crawl(self):
        pass

    def post_crawl(self):
        zip_ref = zipfile.ZipFile(self.tmp_filepath, 'r')
        zip_ref.extractall(self.filepath)
        zip_ref.close()

        filepath_origin = os.path.join(self.filepath, self.get_target().replace(".zip", ".json"))
        filepath_target = os.path.join(self.filepath, "timesheet.json")

        os.rename(filepath_origin, filepath_target)

    def get_target(self):
        return datetime.datetime.now().strftime("%Y%m%d.zip")

if __name__ == "__main__":
    crawler = TRACrawler()
    crawler.run()
