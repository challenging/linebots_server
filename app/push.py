# -*- coding: utf-8 -*-

import os
import time
import click
import random

import logging
logging.basicConfig(filename=os.path.join(os.path.dirname(__file__), "{}.log".format(os.path.basename(__file__))),
                    format='%(asctime)s %(levelname)s %(message)s'
                   )

from lib.push.linebots import booking

@click.command()
def run():
    while True:
        logging.info("start to process cracker tasks of TRA")
        booking()
        logging.info("end the cracker tasks of TRA")

        time.sleep(random.randint(30, 60))

if __name__ == "__main__":
    run()
