#!/usr/bin/env python

import time
import urllib2

from lib.common.utils import check_folder

class Crawler(object):
    def __init__(self, baseurl, filepath):
        self.baseurl = baseurl

        self.filepath = filepath
        check_folder(self.filepath)

        self.tmp_filepath = "/tmp/{}".format(int(time.time()))

    def run(self):
        self.pre_crawl()
        self.crawl()
        self.post_crawl()

    def get_target(self):
        raise NotImplementedError

    def pre_crawl(self):
        raise NotImplementedError

    def crawl(self):
        url = self.baseurl + "/" + self.get_target()
        response = urllib2.urlopen(url)
        with open(self.tmp_filepath, "wb") as out_file:
            out_file.write(response.read())

    def post_crawl(self):
        raise NotImplementedError
