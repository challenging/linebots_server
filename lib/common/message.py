#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

def article():
    return "瀏覽 Google Search 文章"
