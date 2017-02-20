#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

from lib.common.db import DB

class ProfileDB(DB):
    table_name = "profile"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), creation_datetime TIMESTAMP, ticket_type VARCHAR(16), taiwan_id VARCHAR(16), phone VARCHAR(32), status VARCHAR(32));".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (user_id, ticket_type);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, ticket_type, taiwan_id, phone="", status=""):
        sql = "INSERT INTO {} VALUES('{}', '{}', '{}', '{}', '{}', '{}');".format(\
                self.table_name, user_id, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ticket_type, taiwan_id, phone, status)

        return self.cmd(sql)

    def get_profile(self, user_id, ticket_type):
        sql = ""

        if ticket_type == "tra":
            sql = "SELECT person_id FROM {} WHERE user_id = '{}' ORDER BY creation_datetime DESC LIMIT 1"
        elif ticket_type == "thsr":
            sql = "SELECT person_id, cellphone FROM {} WHERE user_id = '{}' ORDER BY creation_datetime DESC LIMIT 1"

        for row in self.select(sql):
            yield row

db_profile = ProfileDB()
