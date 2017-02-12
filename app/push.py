# -*- coding: utf-8 -*-

import os
import time
import click
import random

from lib.common.utils import log
from lib.push.linebots import booking_tra_ticket, booking_thsr_ticket

@click.command()
def run():
    while True:
        booking_tra_ticket()
        booking_thsr_ticket()

        time.sleep(random.randint(15, 30))

if __name__ == "__main__":
    run()
