#!/usr/bin/env python

from lib.push.linebots import push_ticket

from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()

@sched.scheduled_job('cron', minute="*")
def booking_tra_tickets():
    push_ticket()

sched.start()

print "the cracking server is started..."
