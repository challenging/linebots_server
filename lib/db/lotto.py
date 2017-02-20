#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

from lib.common.db import DB
from lib.common.utils import UTF8

class LottoDB(DB):
    table_name = "lotto"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), user_name VARCHAR(128), creation_datetime TIMESTAMP, money INT);".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (user_id);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, user_name, money):
        try:
            sql = "INSERT INTO {} VALUES('{}', '{}', '{}', {});".format(\
                self.table_name, user_id, user_name, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), money)
        except UnicodeEncodeError as e:
            sql = "INSERT INTO {} VALUES('{}', '{}', '{}', {});".format(\
                self.table_name, user_id, user_name.encode(UTF8), datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), money)

        return self.cmd(sql)

db_lotto = LottoDB()

if __name__ == "__main__":
    db_lotto.ask('Ua5f08ec211716ba22bef87a8ac2ca6ee', "陳榮錡", 10)
    for row in db_lotto.query():
        print row

    #db_lotto.delete()
    db_lotto.close()
