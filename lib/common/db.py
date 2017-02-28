#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lib.common.utils import get_db_connection, log

class DB(object):
    table_name = NotImplementedError

    def __init__(self):
        self.conn = get_db_connection()
        self.create_table()

    def create_table(self):
        raise NotImplementedError

    def cmd(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        cursor.close()

        log(sql)

        return cursor.rowcount

    def select(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)

        for row in cursor.fetchall():
            yield row

        cursor.close()

    def ask(self, user_id, user_name, question, answer):
        raise NotImplementedError

    def query(self, user_id=None):
        cursor = self.conn.cursor()

        sql = "SELECT * FROM {} ORDER BY creation_datetime DESC".format(self.table_name)
        if user_id is not None:
            sql = "SELECT * FROM {} WHERE user_id = '{}' ORDER BY creation_datetime DESC;".format(self.table_name, user_id)

        for row in self.select(sql):
            yield row

    def delete(self):
        sql = "DELETE FROM {}".format(self.table_name)

        return self.cmd(sql)

    def drop(self):
        sql = "DROP TABLE {}".format(self.table_name)

        return self.cmd(sql)
