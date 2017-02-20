#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

from lib.common.db import DB

class ProfileDB(DB):
    table_name = "profile"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), creation_datetime TIMESTAMP, ticket_type VARCHAR(16), param VARCHAR(1024), status VARCHAR(32));".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (user_id, ticket_type);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, ticket_type, param):
        sql = "INSERT INTO {} VALUES('{}', '{}', '{}', '{}', null);".format(\
                self.table_name, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, param)

        return self.cmd(sql)

    def get_profile(self, user_id, ticket_type):
        sql = "SELECT param FROM {} WHERE user_id = '{}' AND ticket_type = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(self.table_name, user_id, ticket_type)

        for row in self.select(sql):
            yield row

db_profile = ProfileDB()

if __name__ == "__main__":
    user_id = "Ua5f08ec211716ba22bef87a8ac2ca6ee"
    for row in db_profile.get_profile(user_id, "thsr"):
        print row
