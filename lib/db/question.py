#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

from lib.common.db import DB
from lib.common.utils import UTF8

class QuestionDB(DB):
    table_name = "question"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS {} (user_id VARCHAR(128), user_name VARCHAR(128), creation_datetime TIMESTAMP, question VARCHAR(2048), answer TEXT);".format(self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_datetime ON {table_name} (creation_datetime);".format(table_name=self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_user_id ON {table_name} (user_id);".format(table_name=self.table_name))
        cursor.execute("CREATE INDEX IF NOT EXISTS {table_name}_question ON {table_name} (question);".format(table_name=self.table_name))
        cursor.close()

    def ask(self, user_id, user_name, question, answer):
        try:
            sql = "INSERT INTO {} VALUES('{}', '{}', '{}', '{}', '{}');".format(\
                    self.table_name, user_id, user_name, datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), question.replace("'", '"'), answer.replace("'", '"'))
        except UnicodeEncodeError as e:
            sql = "INSERT INTO {} VALUES('{}', '{}', '{}', '{}', '{}');".format(\
                    self.table_name, user_id, user_name.encode(UTF8), datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), question.replace("'", '"'), answer.replace("'", '"'))

        return self.cmd(sql)

db_question = QuestionDB()

if __name__ == "__main__":
    db_question.ask(1111, "陳榮錡", "650喬治商職", "嗨！ Rungchi Chen,綠2左保平路口往[中永和]方向 預估 4.3 分鐘到達")

    questions = []
    for row in db_question.query():
        questions.append("\t".join(r if isinstance(r, (str, unicode)) else str(r) for r in row))

    db_question.close()

    print "\n".join(questions)
