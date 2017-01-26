#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import geocoder
import requests

import logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from tqdm import tqdm

UTF8 = "UTF8"
MONEY = 25

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.environ["LINEBOT_CHANNEL_SECRET"]
channel_access_token = os.environ["LINEBOT_CHANNEL_TOKEN"]

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

def help():
    msg = """感謝您使用 Bot of LazyRC Inc. 目前此機器人支援下列問題
1. 公車查詢 (輸入：<公車號碼><站牌名稱>, 例: 650喬治商職)
2. 天氣（輸入：<台灣縣市>, 例：台北）
3. 星座運勢（輸入：<星座>, 例：射手）
4. 匯率（輸入：<幣別>, 例：美金）
5. 若查詢不到，則會以 google search 第一筆搜尋結果為答案"""

    return msg

def error():
    return """系統發生錯誤，請稍後再試，感謝您的耐心！"""

def not_support():
    return """電腦版不支援，請使用手機版，方可正常顯示訊息"""

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
