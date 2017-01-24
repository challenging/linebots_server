#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

from lib.common.db import DB

class LocationDB(DB):
    table_name = "location"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), creation_datetime TIMESTAMP, lat DECIMAL(10, 7), lng DECIMAL(10, 7));".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (user_id);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, lat, lng):
        sql = "INSERT INTO {} VALUES('{}', '{}', {}, {});".format(\
                self.table_name, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), lat, lng)

        cursor = self.conn.cursor()
        cursor.execute(sql)
        cursor.close()

db_location = LocationDB()

if __name__ == "__main__":
    db_location.ask('Ua5f08ec211716ba22bef87a8ac2ca6ee', 25.026187254, 121.542108469)
    for row in db_location.query():
        print row

    db_location.close()
