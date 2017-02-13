#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lib.common.utils import MODE_NORMAL, MODE_LOTTO, MODE_TRA_TICKET, MODE_THSR_TICKET

def txt_hello(user_name, answer):
    return "嗨！ {},\n{}".format(user_name, answer)

def txt_help():
    msg = """LazyRC支援三種模式（請輸入「切換模式」）
 1.[查詢模式]
    - 公車查詢 (例: 18師大)
    - 天氣（例：台北）
    - 星座運勢（例：射手）
    - 匯率（例：美金）
    - 若查詢不到，回傳 google search 結果
 2.[台鐵訂票模式]
 3.[高鐵訂票模式]"""

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

def txt_location():
    return "顯示位置在地圖上"

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
    elif mode == MODE_TRA_TICKET:
        mode_name = "台鐵訂票"
        comments = "(請先輸入身份證字號)"
    elif mode == MODE_THSR_TICKET:
        mode_name = "高鐵訂票"
        comments = "(請先輸入身份證字號)"
    else:
        pass

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
