#!/usr/bin/env python

from apscheduler.schedulers.blocking import BlockingScheduler
from lib.bot import fxrate, weather, lucky, bus

sched = BlockingScheduler()

fxrate.bot.init()
weather.bot.init()
lucky.bot.init()
bus.bot.init()
bus.bot.hourly_job()

@sched.scheduled_job('interval', minutes=15)
def weather_job():
    weather.bot.crawl_job()

@sched.scheduled_job('interval', minutes=1)
def fxrate_job():
    fxrate.bot.crawl_job()

@sched.scheduled_job('cron', hour="7,8,9")
def lucky_job():
    lucky.bot.crawl_job()

@sched.scheduled_job('interval', hours=6)
def bus_stop_job():
    bus.bot.hourly_job()

@sched.scheduled_job('interval', seconds=55)
def bus_time_job():
    bus.bot.crawl_job()

sched.start()

print "the crawling server is started..."
