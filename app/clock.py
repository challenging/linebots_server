#!/usr/bin/env python

from lib.push.linebots import booking

from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()

@sched.scheduled_job('cron', minute="*")
def booking_tra_tickets():
    booking()

sched.start()

print "the cracking server is started..."
