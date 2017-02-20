#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

from lib.common.db import DB
from lib.common.utils import MODE_NORMAL

class ModeDB(DB):
    table_name = "mode"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), creation_datetime TIMESTAMP, mode VARCHAR(16));".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (user_id);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, mode="normal"):
        sql = "INSERT INTO {} VALUES('{}', '{}', '{}');".format(\
                self.table_name, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), mode)

        return self.cmd(sql)

    def query(self, user_id):
        sql = "SELECT mode, creation_datetime FROM {} WHERE user_id = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(self.table_name, user_id)

        mode = MODE_NORMAL
        for row in self.select(sql):
            mode = row[0].lower()

        return mode

db_mode = ModeDB()

if __name__ == "__main__":
    db_mode.ask('Ua5f08ec211716ba22bef87a8ac2ca6ee')
    for row in db_mode.query():
        print row

    db_mode.delete()
    db_mode.close()
