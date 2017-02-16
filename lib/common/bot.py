#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

import psycopg2
import urlparse
import datetime

from lib.common.utils import log, get_db_connection
from lib.common.utils import UTF8

class Bot(object):
    repository = "Bot"
    filename = "bot.json"

    def __init__(self):
        self.dataset = []
        self.info = {}

        self.init_table()

    def init_table(self):
        self.conn = get_db_connection()

        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (question VARCHAR(128), creation_datetime TIMESTAMP, answer TEXT);".format(self.repository))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_idx ON {table_name} (creation_datetime, question);".format(table_name=self.repository))
        cursor.close()

        self.cursor = self.conn.cursor()

    def init(self):
        self.set_dataset()
        self.crawl_job()
        self.gen_results()
        self.insert_answer()

    def insert_answer(self):
        rows = []

        cursor = self.conn.cursor()
        for question, answer in self.info.items():
            try:
                rows.append("('{}', '{}', '{}')".format(question, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), json.dumps(answer)))
            except UnicodeDecodeError as e:
                rows.append("('{}', '{}', '{}')".format(question.encode(UTF8), datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), json.dumps(answer)))

        if rows:
            sql = "TRUNCATE TABLE {}".format(self.repository)
            cursor.execute(sql)

            sql = "INSERT INTO {} VALUES {}".format(self.repository, ",".join(rows))
            cursor.execute(sql)

            log("The {} bot finish updating answers".format(type(self).__name__))

        cursor.close()

    def set_dataset(self):
        raise NotImplementedError

    def crawl_job(self, is_gen=False):
        raise NotImplementedError

    def gen_results(self):
        raise NotImplementedError

    def ask(self, question):
        creation_datetime, answer = None, None

        sql = "SELECT creation_datetime, answer FROM {} WHERE question = '{}' ORDER BY creation_datetime DESC LIMIT 1".format(self.repository, question)

        self.cursor.execute(sql)
        for row in self.cursor.fetchall():
            creation_datetime, answer = row
            answer = json.loads(answer)

        return creation_datetime, answer

    def bots(self, msg):
        raise NotImplementedError

    def close(self):
        self.conn.close()
