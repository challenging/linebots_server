#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import psycopg2
import urlparse
import datetime

class NotificationQueueDB(object):
    def __init__(self):
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.environ["DATABASE_URL"])

        self.conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )

        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS notification (user_id VARCHAR(128), notification_type VARCHAR(64), creation_datetime TIMESTAMP, notification_datetime TIMESTAMP, memo VARCHAR(128));")
        cursor.execute("CREATE INDEX IF NOT EXISTS notification_idx ON notification (notification_datetime)")
        cursor.close()

    def book(self, user_id, notification_type, notification_datetime, memo):
        sql = "INSERT INTO notification VALUES('{}', '{}', '{}', '{}', '{}');".format(\
            user_id, notification_type, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), notification_datetime, memo)

        cursor = self.conn.cursor()
        cursor.execute(sql)
        cursor.close()

    def query(self):
        cursor = self.conn.cursor()

        cursor.execute("SELECT user_id, notification_type, memo FROM notification;")
        for row in cursor.fetchall():
            yield row

        cursor.close()

    def close(self):
        self.conn.close()

db = NotificationQueueDB()

if __name__ == "__main__":
    db.book("Ua5f08ec211716ba22bef87a8ac2ca6ee", "weather", "2017-01-16T11:10:00", "桃園")
    db.book("Ua5f08ec211716ba22bef87a8ac2ca6ee", "bus", "2017-01-16T11:10:00", "650喬治商職")
    db.book("Ua5f08ec211716ba22bef87a8ac2ca6ee", "lucky", "2017-01-16T11:10:00", "射手座")

    db.book("Uf97b5034ef9534329fba1a3dad4b09e7", "weather", "2017-01-16T11:10:00", "桃園")
    db.book("Uf97b5034ef9534329fba1a3dad4b09e7", "bus", "2017-01-16T11:10:00", "235捷運西門站")
    db.book("Uf97b5034ef9534329fba1a3dad4b09e7", "lucky", "2017-01-16T11:10:00", "摩羯座")

    for row in db.query():
        print row

    db.close()
