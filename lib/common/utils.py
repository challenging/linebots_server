#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import geocoder
import requests
import psycopg2
import urlparse

import logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from tqdm import tqdm
from selenium import webdriver

UTF8 = "UTF8"
CONN = None

MODE_NORMAL = "normal"
MODE_LOTTO = "lotto"
MODE_TICKET = "ticket"

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.environ["LINEBOT_CHANNEL_SECRET"]
channel_access_token = os.environ["LINEBOT_CHANNEL_TOKEN"]

def get_chrome_driver():
    # Set chrome driver path
    chromedriver = os.path.join(data_dir("driver"), "chromedriver_{}".format("mac64" if sys.platform == "darwin" else "linux64"))
    if not os.path.exists(chromedriver):
        print "Not found the driver of Chrome from {}".format(chromedriver)
    else:
        os.environ["webdriver.chrome.driver"] = chromedriver
        print "export webdriver.chrome.driver={}".format(chromedriver)

    return webdriver.Chrome(chromedriver)

def get_phantom_driver():
    driver = os.path.join(data_dir("driver"), "phantomjs-2.1.1-{}".format("mac64" if sys.platform == "darwin" else "linux64"), "bin", "phantomjs")

    if not os.path.exists(driver):
        print "Not found the driver of PhantomJS from {}".format(driver)

    print driver
    return webdriver.PhantomJS(driver)

def get_db_connection():
    global CONN

    if CONN is None:
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.environ["DATABASE_URL"])

        CONN = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
        )

        CONN.autocommit = True

    return CONN

def check_folder(filepath, is_folder=False):
    folder = filepath
    if not is_folder:
        folder = os.path.dirname(filepath)

    if not os.path.exists(folder):
        os.makedirs(folder)

def data_dir(subfolder):
    return os.path.join(os.path.dirname(__file__), "..", "..", "etc", subfolder)

def db_dir():
    return data_dir("db")

def crawl(url, subfolder, filename=None, compression=True):
    filename = filename if filename is not None else url.split("/")[-1]

    filename = os.path.join(data_dir(subfolder), "{}.bak".format("{}.gz".format(filename) if compression else filename))
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
        print "Create {} to be the repository for the data of {}".format(os.path.dirname(filename), subfolder)

    response = requests.get(url, stream=True)

    is_pass = False
    with open(filename, "wb") as handle:
        try:
            for data in tqdm(response.iter_content()):
                handle.write(data)

            print "Save {} in {} successfully".format(url, filename)
            is_pass = True
        except AttributeError as e:
            print "Save {} in {} failed".format(url, filename)

    if is_pass:
        # rename file
        os.rename(filename, filename.rsplit(".", 1)[0])

def is_admin(user_id):
    if user_id == "Ua5f08ec211716ba22bef87a8ac2ca6ee":
        return True
    else:
        return False

def get_rc_id():
    return "Ua5f08ec211716ba22bef87a8ac2ca6ee"

def get_location(lat, lng):
    return geocoder.google([lat, lng], method='reverse')

def read_cfg(filepath):
    import ConfigParser

    config = ConfigParser.RawConfigParser()
    config.read(filepath)

    return config

if __name__ == "__main__":
    g = get_location(24.58610, 120.82952)

    print g, g.city, g.state, g.county
