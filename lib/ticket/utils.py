#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
import urllib
import urllib2

from lib.common.utils import check_folder, data_dir, get_phantom_driver

TICKET_RETRY = 4
TICKET_COUNT = 4

TICKET_STATUS_BOOKED = "booked"
TICKET_STATUS_UNSCHEDULED = "unscheduled"
TICKET_STATUS_CANCELED = "canceled"
TICKET_STATUS_SCHEDULED = "scheduled"
TICKET_STATUS_MEMORY = "memory"
TICKET_STATUS_FORGET = "forget"
TICKET_STATUS_FAILED = "failed"
TICKET_STATUS_AGAIN = "again"
TICKET_STATUS_CONFIRM = "confirm"
TICKET_STATUS_RETRY = "retry"
TICKET_STATUS_SPLIT = "split"
TICKET_STATUS_PAY = "pay"

TICKET_CMD_QUERY = set(["query", "查詢", "記錄", "list"])
TICKET_CMD_RESET = set(["reset", "重設", "清空", "重來", "again", "clear", "清除"])

TICKET_HEADERS_BOOKED_TRA = [u"懶人ID", u"票號", u"車次/車種", u"搭乘時間", u"起迄站"]
TICKET_HEADERS_BOOKED_THSR = [u"懶人ID", u"票號", u"車廂", u"車次", u"搭乘時間", u"起迄站", u"票數", u"付款金額"]

URL_TRA = "http://railway1.hinet.net/csearch.htm"
URL_TRAINNO_TRA = "http://railway.hinet.net/ctno1.htm"

TIMESHEET_TRA = "/Users/rongqichen/Documents/programs/line_bots/github/etc/captcha/tra/timesheet.json"

def load_tra_trainno(filepath=os.path.join(data_dir("captcha"), "tra", "timesheet.json")):
    timesheet = None
    with open(filepath, "rb") as in_file:
        timesheet = json.load(in_file)

    trains = set()
    for train in timesheet["TrainInfos"]:
        trains.add(train["Train"])

    return trains

def tra_dir(f):
    folder = os.path.join(data_dir("captcha"), "tra", f)
    check_folder(folder, is_folder=True)

    return folder

def tra_img_dir():
    return tra_dir("source")

def tra_screen_dir():
    return tra_dir("screenshot")

def tra_success_dir():
    return tra_dir("success")

def tra_fail_dir():
    return tra_dir("fail")

def tra_ticket_dir():
    return tra_dir("ticket")

tra_train_type = {"自強號": "*1", "莒光號": "*2", "復興號": "*3", "全部車種": "*4"}
tra_stations = {
    "台東": "004",
    "鹿野": "008",
    "瑞源": "009",
    "關山": "012",
    "池上": "015",
    "富里": "018",
    "東竹": "020",
    "東里": "022",
    "玉里": "025",
    "瑞穗": "029",
    "富源": "031",
    "光復": "034",
    "萬榮": "035",
    "鳳林": "036",
    "南平": "037",
    "豐田": "040",
    "壽豐": "041",
    "志學": "043",
    "吉安": "045",
    "花蓮": "051",
    "北埔": "052",
    "新城": "054",
    "崇德": "055",
    "和仁": "056",
    "和平": "057",
    "南澳": "062",
    "東澳": "063",
    "蘇澳": "066",
    "蘇澳新": "067",
    "冬山": "069",
    "羅東": "070",
    "二結": "072",
    "宜蘭": "073",
    "四城": "074",
    "礁溪": "075",
    "頭城": "077",
    "龜山": "079",
    "大溪": "080",
    "大里": "081",
    "褔隆": "083",
    "貢寮": "084",
    "雙溪": "085",
    "牡丹": "086",
    "三貂嶺": "087",
    "猴硐": "088",
    "瑞芳": "089",
    "四腳亭": "090",
    "基隆": "092",
    "八堵": "093",
    "七堵": "094",
    "汐止": "096",
    "南港": "097",
    "松山": "098",
    "台北": "100",
    "萬華": "101",
    "板橋": "102",
    "樹林": "103",
    "山佳": "104",
    "鶯歌": "105",
    "桃園": "106",
    "內壢": "107",
    "中壢": "108",
    "埔心": "109",
    "楊梅": "110",
    "富岡": "111",
    "湖口": "112",
    "新豐": "113",
    "竹北": "114",
    "新竹": "115",
    "竹南": "118",
    "談文": "119",
    "大山": "120",
    "後龍": "121",
    "白沙屯": "123",
    "新埔": "124",
    "通霄": "125",
    "苑裡": "126",
    "日南": "127",
    "大甲": "128",
    "台中港": "129",
    "清水": "130",
    "沙鹿": "131",
    "龍井": "132",
    "大肚": "133",
    "追分": "134",
    "造橋": "135",
    "苗栗": "137",
    "銅鑼": "139",
    "三義": "140",
    "泰安": "142",
    "后里": "143",
    "豐原": "144",
    "潭子": "145",
    "台中": "146",
    "烏日": "147",
    "成功": "148",
    "彰化": "149",
    "花壇": "150",
    "員林": "151",
    "社頭": "153",
    "田中": "154",
    "二水": "155",
    "林內": "156",
    "斗六": "158",
    "斗南": "159",
    "大林": "161",
    "民雄": "162",
    "嘉義": "163",
    "水上": "164",
    "後壁": "166",
    "新營": "167",
    "林鳳營": "169",
    "隆田": "170",
    "拔林": "171",
    "善化": "172",
    "新市": "173",
    "永康": "174",
    "台南": "175",
    "保安": "176",
    "中洲": "177",
    "大湖": "178",
    "路竹": "179",
    "岡山": "180",
    "橋頭": "181",
    "楠梓": "183",
    "左營": "184",
    "高雄": "185",
    "鳳山": "186",
    "後庄": "187",
    "九曲堂": "188",
    "屏東": "190",
    "西勢": "193",
    "竹田": "194",
    "潮州": "195",
    "南州": "197",
    "林邊": "199",
    "佳冬": "200",
    "枋寮": "203",
    "加祿": "204",
    "大武": "211",
    "瀧溪": "213",
    "金崙": "215",
    "太麻里": "217",
    "知本": "219",
    "康樂": "220",
    "大慶": "223",
    "十分": "232",
    "平溪": "235",
    "內灣": "248",
    "車埕": "256",
    "新烏日": "280",
    "南科": "282",
    "新左營": "288"
}

def get_station_name(station_number):
    station_name = None
    for k, v in tra_stations.items():
        if v == station_number:
            station_name = k

            break

    return station_name

def get_train_name(train_type):
    train_name = None
    for k, v in tra_train_type.items():
        if v == train_type:
            train_name = k

            break

    return train_name

get_station_number = lambda station_name: tra_stations.get(station_name, None)
get_train_type = lambda train_name: tra_train_type.get(train_name, None)

thsr_stations = set(["南港", "台北", "板橋", "桃園", "新竹", "苗栗", "台中", "彰化", "雲林", "嘉義", "台南", "左營"])

def get_thsr_url(booking_type):
    url = "https://irs.thsrc.com.tw/IMINT/"

    if booking_type == "general":
        url = "https://irs.thsrc.com.tw/IMINT/"
    elif booking_type == "student":
        url = "https://irs.thsrc.com.tw/IMINT/?student=university"
    elif booking_type == "credit":
        url = "https://irs.thsrc.com.tw/IMINT/creditcard"

    return url

def thsr_dir(f):
    folder = os.path.join(data_dir("captcha"), "thsr", f)
    check_folder(folder, is_folder=True)

    return folder

def thsr_img_dir():
    return thsr_dir("source")

def thsr_screen_dir():
    return thsr_dir("screenshot")

def thsr_success_dir():
    return thsr_dir("success")

def thsr_fail_dir():
    return thsr_dir("fail")

def thsr_ticket_dir():
    return thsr_dir("ticket")

def thsr_cancel_dir():
    return thsr_dir("cancel")

class TRAUtils(object):
    TRA_CANCELED_URL = "http://railway.hinet.net/ccancel_rt.jsp"
    TRA_QUERY_URL = "http://railway.hinet.net/coquery.jsp"

    @staticmethod
    def is_canceled(person_id, ticket_number):
        url = "{}?personId={}&orderCode={}".format(self.TRA_CANCELED_URL, person_id.upper(), ticket_number)

        '''
        request = urllib2.Request(url, headers=headers)
        f = urllib2.urlopen(request)
        content = unicode(f.read(), f.headers.getparam('charset'))
        '''

        opener = get_phantom_driver()
        opener.get(url)
        content = opener.find_element_by_xpath("//p[@class='orange02']").text

        is_passing = False
        if content == u"您的車票取消成功":
            is_passing = True

        opener.quit()

        return is_passing

    @staticmethod
    def get_status(person_id, ticket_number):
        status = None

        req = urllib2.Request("{}?personId={}&orderCode={}".format(TRAUtils.TRA_QUERY_URL, person_id, ticket_number))
        req.add_header("Referer", "http://railway.hinet.net/coquery.htm")
        req.add_header("Uesr-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/602.4.8 (KHTML, like Gecko) Version/10.0.3 Safari/602.4.8")

        f = urllib2.urlopen(req)
        content = unicode(f.read(), f.headers.getparam('charset'))

        if content.find("&#24744;&#35330;&#30340;&#36554;&#31080;&#24050;&#32147;&#30001;") > -1 and content.find("&#20184;&#27454;") > -1:
            status = TICKET_STATUS_PAY
        elif content.find("&#24744;&#35330;&#30340;&#36554;&#31080;&#24050;&#21462;&#28040;") > -1:
            status = TICKET_STATUS_CANCELED

        return status

if __name__ == "__main__":
    #print TRAUtils.get_status("l122760167", "977287")
    #print TRAUtils.get_status("l122760167", "208433")

    '''
    timesheet_tra = load_tra_timesheep()
    for k in timesheet_tra["TrainInfos"]:
        print k["Train"]
    '''

    print TRAUtils.is_canceled("l122760167", "577707")
