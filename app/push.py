# -*- coding: utf-8 -*-

import os
import time
import click
import random

from lib.common.utils import log
from lib.push.linebots import booking

@click.command()
def run():
    while True:
        log("start to process cracker tasks of TRA")
        booking()
        log("end the cracker tasks of TRA")

        time.sleep(random.randint(30, 60))

if __name__ == "__main__":
    run()
