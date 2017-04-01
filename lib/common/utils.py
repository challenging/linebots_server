#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import inspect
import geocoder
import requests
import psycopg2
import urlparse

import ConfigParser

import logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)

from tqdm import tqdm
from selenium import webdriver

UTF8 = "UTF8"
CONN = None
LINEBOTS = "LINEBOTS"

MODES = set(["切換模式", "qoo"])
MODE_NORMAL = "normal"
MODE_LOTTO = "lotto"
MODE_TRA_TICKET = "ticket_tra"
MODE_THSR_TICKET = "ticket_thsr"

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.environ["LINEBOT_CHANNEL_SECRET"]
channel_access_token = os.environ["LINEBOT_CHANNEL_TOKEN"]

def get_chrome_driver():
    # Set chrome driver path
    chromedriver = os.path.join(data_dir("driver"), "chromedriver_{}".format("mac64" if sys.platform == "darwin" else "linux64"))
    if not os.path.exists(chromedriver):
        log("Not found the driver of Chrome from {}".format(chromedriver))
    else:
        os.environ["webdriver.chrome.driver"] = chromedriver
        log("export webdriver.chrome.driver={}".format(chromedriver))

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--incognito")

    opener = webdriver.Chrome(chromedriver, chrome_options=chrome_options)

    # Safari Driver
    #from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    #opener = webdriver.Remote(command_executor='http://127.0.0.1:4444/wd/hub', desired_capabilities=DesiredCapabilities.SAFARI)

    return opener

def get_firefox_driver()
    opener = webdriver.Firefox(executable_path=os.path.join(data_dir("driver"), "geckodriver"))

    return opener

def get_phantom_driver():
    driver = os.path.join(data_dir("driver"), "phantomjs-2.1.1-{}".format("mac64" if sys.platform == "darwin" else "linux64"), "bin", "phantomjs")

    if not os.path.exists(driver):
        log("Not found the driver of PhantomJS from {}".format(driver))

    return webdriver.PhantomJS(driver)

def get_driver(driver):
    if driver.lower() == "chrome":
        return get_chrome_driver()
    elif driver.lower() == "firefox":
        return get_firefox_driver()
    else:
        return get_phantom_driver()

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
                port=url.port,
                connect_timeout=60
        )

        CONN.autocommit = True

    return CONN

def db_reconnect():
    global CONN

    if CONN is not None:
        CONN.close()

    return get_db_connection()

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
        log("Create {} to be the repository for the data of {}".format(os.path.dirname(filename), subfolder))

    response = requests.get(url, stream=True)

    is_pass = False
    with open(filename, "wb") as handle:
        try:
            for data in tqdm(response.iter_content()):
                handle.write(data)

            log("Save {} in {} successfully".format(url, filename))
            is_pass = True
        except AttributeError as e:
            log("Save {} in {} failed".format(url, filename))

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
    config = ConfigParser.RawConfigParser()
    config.read(filepath)

    return config

def log(message):
    global logging

    logging.info("{}\t{}\t{}".format(str(inspect.getmodule(inspect.stack()[1][0])).split(" ")[1], inspect.stack()[1][3], message))

if __name__ == "__main__":
    g = get_location(24.58610, 120.82952)

    print g, g.city, g.state, g.county
