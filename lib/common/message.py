#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lib.common.utils import MODE_NORMAL, MODE_LOTTO, MODE_TICKET

def txt_hello(user_name, answer):
    return "嗨！ {},\n{}".format(user_name, answer)

def txt_help():
    msg = """感謝您使用 Bot of LazyRC Inc. 目前此機器人支援下列問題
1. 公車查詢 (輸入：<公車號碼><站牌名稱>, 例: 650喬治商職)
2. 天氣（輸入：<台灣縣市>, 例：台北）
3. 星座運勢（輸入：<星座>, 例：射手）
4. 匯率（輸入：<幣別>, 例：美金）
5. 若查詢不到，則會以 google search 第一筆搜尋結果為答案"""

    return msg

def txt_google(msg, answer):
    return "我不清楚你的問題[{}]，所以提供 google search 結果\n{}".format(msg, answer)

def txt_error():
    return "系統發生錯誤，請稍後再試，感謝您的耐心！"

def txt_not_found_answer(question, mode):
    return "Not found answer for {} based on {} mode".format(question, mode)

def txt_not_support():
    return "電腦版不支援，請使用手機版，方可正常顯示訊息"

def txt_article():
    return "瀏覽 Google Search 文章"

def txt_error_location():
    return "尚無設定地理位置，請設定後，即可得到正確天氣資訊。"

def txt_error_lucky():
    return "尚無設定星座，請設定後，即可得到星座運勢。"

def txt_mode(mode):
    mode_name, comments = None, None

    if mode == MODE_NORMAL:
        mode_name = "查詢"
        comments = "(輸入help，有入門導覽指引)"
    elif mode == MODE_LOTTO:
        mode_name = "競標"
        comments = ""
    elif mode == MODE_TICKET:
        mode_name = "訂票"
        comments = "(請先輸入身份證字號)"

    return "目前模式為{}{}".format(mode_name, comments)

def txt_ticket_title():
    return "懶人訂票服務"

def txt_ticket_body():
    return "請選擇下列票種"

def txt_ticket(mode):
    t = None
    if mode == "tra":
        t = "台鐵"
    elif mode == "thsr":
        t = "高鐵"
    elif mode == "fly":
        t = "飛機"

    return "訂購 {} 票".format(t)
