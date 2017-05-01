#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import time
import random
import datetime

from PIL import Image

from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

from lib.ocr.cracker import init_model, crack_thsr
from lib.common.utils import UTF8
from lib.common.utils import check_folder, get_driver, log
from lib.ocr.utils import get_digest
from lib.ticket.utils import get_thsr_url
from lib.ticket.utils import thsr_img_dir, thsr_screen_dir, thsr_success_dir, thsr_fail_dir, thsr_ticket_dir, thsr_cancel_dir

init_model("thsr")

def book_ticket(param, driver="phantom"):
    opener = get_driver(driver)

    retry, ticket_number = 2, None
    train_type, train_count, train_number, start_station, end_station, date, stime, etime, money = None, None, None, None, None, None, None, None, None
    while retry >= 0:
        opener.get(get_thsr_url(param["booking_type"]))

        # choose started station
        station = param["selectStartStation"]
        if isinstance(station, str):
            station = unicode(param["selectStartStation"], UTF8)

        try:
            select = Select(opener.find_element_by_name("selectStartStation"))
            select.select_by_visible_text(station)
        except NoSuchElementException as e:
            continue

        # choose destination station
        station = param["selectDestinationStation"]
        if isinstance(station, str):
            station = unicode(param["selectDestinationStation"], UTF8)

        select = Select(opener.find_element_by_name("selectDestinationStation"))
        select.select_by_visible_text(station)

        # only show the early bird tickets
        if param["onlyQueryOffPeakCheckBox"]:
            opener.find_element_by_id("onlyQueryOffPeakCheckBox").click()

        # preferred seat
        opener.find_element_by_id(param["preferred_seat"])
        # preferred booking method
        opener.find_element_by_id(param["booking"])
        # preferred date
        input_field = opener.find_element_by_id('toTimeInputField')
        input_field.clear()
        input_field.send_keys(param["booking_date"])
        # preferred time
        #opener.find_element_by_name("toTimeTable").send_keys(param["booking_stime"])
        select = Select(opener.find_element_by_name("toTimeTable"))
        select.select_by_visible_text(param["booking_stime"])
        # ticket amount
        if param["ticketPanel:rows:0:ticketAmount"] != 1:
            opener.find_element_by_name("ticketPanel:rows:0:ticketAmount").send_keys(param["ticketPanel:rows:0:ticketAmount"])

        if param["booking_type"] == "student":
            tc = param.get("ticketPanel:rows:4:ticketAmount", 0)
            if tc != 1:
                opener.find_element_by_name("ticketPanel:rows:4:ticketAmount").send_keys(tc)

        if "ticketPanel:rows:1:ticketAmount" in param:
            tc = param.get("ticketPanel:rows:1:ticketAmount", 0)
            if tc != 1:
                opener.find_element_by_name("ticketPanel:rows:1:ticketAmount").send_keys(param["ticketPanel:rows:1:ticketAmount"])

        retry_crack = 4
        while retry_crack > 0:
            try:
                img = opener.find_element_by_id("BookingS1Form_homeCaptcha_passCode")
                location, size = img.location, img.size

                if not isinstance(opener, webdriver.PhantomJS):
                    location["x"] *= 2
                    location["y"] *= 2
                    size["width"] *= 2
                    size["height"] *= 2
                else:
                    location["x"] += 5

                filepath_screenshot = os.path.join(thsr_screen_dir(), "{}.jpg".format(int(1000*time.time())))
                opener.save_screenshot(filepath_screenshot)
                log("save image in {}".format(filepath_screenshot))

                im = Image.open(filepath_screenshot)
                im = im.crop((location["x"], location["y"], location["x"]+size["width"], location["y"] + size["height"]))

                if not isinstance(opener, webdriver.PhantomJS):
                    im = im.resize((im.size[0]/2, im.size[1]/2), Image.ANTIALIAS)

                im_filepath = os.path.join(thsr_img_dir(), "{}.jpg".format(get_digest(im)))
                check_folder(im_filepath)
                im.save(im_filepath)
                log("save cropped image in {}".format(im_filepath))

                answer = crack_thsr(im_filepath)

                submit = opener.find_element_by_name("homeCaptcha:securityCode")
                submit.clear()
                submit.send_keys(answer)

                opener.find_element_by_id("BookingS1Form").submit()

                try:
                    # go to the next step
                    time.sleep(random.randint(1, 4))

                    opener.find_element_by_id("BookingS2Form")
                    retry_crack = -1

                    break
                except NoSuchElementException as nee:
                    opener.find_element_by_id("BookingS1Form_homeCaptcha_reCodeLink").click()
                    time.sleep(random.randint(2, 4))
            except NoSuchElementException as nee:
                pass

            retry_crack -= 1

        trains = []
        for field in opener.find_elements_by_xpath("//tr"):
            if field.get_attribute("onMouseOver"):
                trains.append(field.text.split())

            for img_field in field.find_elements_by_tag_name("img"):
                trains[-1].append(img_field.get_attribute("src"))

            for radio_field in field.find_elements_by_name("TrainQueryDataViewPanel:TrainGroup"):
                trains[-1].append(radio_field)

        button = None
        stime, etime = datetime.datetime.strptime(param["booking_stime"], "%H:%M"), datetime.datetime.strptime(param["booking_etime"], "%H:%M")
        for train in trains:
            t = datetime.datetime.strptime(train[1], "%H:%M")

            if stime <= t and etime >= t:
                button = train[-1]

            if button:
                break
        button.click()

        form = opener.find_element_by_id("BookingS2Form")
        form.submit()
        time.sleep(random.randint(1, 3))

        ticket_info = opener.find_element_by_xpath("//table[@class='table_simple']")
        for idx, info in enumerate(ticket_info.text.split("\n")[1:]):
            if param["booking_type"] != "student":
                if idx == 0:
                    print re.split("[\s]+", info)
                    print len(re.split("[\s]+", info))
                    _, date, train_number, start_station, end_station, stime, etime, _, _, _, money = re.split("[\s]+", info)
                elif idx == 1:
                    t = re.split("[\s]+", info)
                    train_type = t[0]
                    train_count = " ".join(t[1:-3])
            else:
                if idx == 0:
                    _, date, train_number, start_station, end_station, stime, etime, _, _ = re.split("[\s]+", info)
                elif idx == 1:
                    _, _, money = re.split("[\s]+", info)
                elif idx == 2:
                    t = re.split("[\s]+", info)
                    train_type = t[0]
                    train_count = " ".join(t[1:-3])

        opener.find_element_by_id("idNumber").send_keys(param["person_id"])
        opener.find_element_by_id("mobileInputRadio").click()
        opener.find_element_by_id("mobilePhone").send_keys(param["cellphone"])
        opener.find_element_by_name("agree").click()
        opener.find_element_by_id("isSubmit").click()
        time.sleep(random.randint(2, 4))

        ticket_number = opener.find_element_by_xpath("//table[@class='table_details']//td[@class='content_key']")
        if ticket_number:
            ticket_number = ticket_number.text

            filepath_ticket = os.path.join(thsr_ticket_dir(), "{}.jpg".format(ticket_number))
            opener.save_screenshot(filepath_ticket)
            log("save ticket image in {}".format(filepath_ticket))

            filepath_success = os.path.join(thsr_success_dir(), "{}.jpg".format(answer))
            os.rename(im_filepath, filepath_success)
            log("book the ticket number - {}".format(ticket_number))

            break
        else:
            retry -= 1

    opener.quit()

    return ticket_number, (train_type, train_count, train_number, start_station, end_station, date, stime, etime, money)

def cancel_ticket(person_id, ticket_number, driver="phantom"):
    is_cancelled = False
    opener = get_driver(driver)

    retry = 3
    while retry > 0 and not is_cancelled:
        opener.get("https://irs.thsrc.com.tw/IMINT/?wicket:bookmarkablePage=:tw.com.mitac.webapp.thsr.viewer.History")

        # step 1
        opener.find_element_by_id("idInputRadio1").click()
        opener.find_element_by_id("rocId").send_keys(person_id)
        opener.find_element_by_name("orderId").send_keys(ticket_number)
        opener.find_element_by_name("SubmitButton").click()

        # step 2
        try:
            opener.find_element_by_name("TicketProcessButtonPanel:CancelSeatsButton").click()
        except NoSuchElementException as e:
            if opener.find_element_by_id("error").text == u"查無此筆記錄":
                is_cancelled = True
                continue

        filepath_canceled_ticket = os.path.join(thsr_cancel_dir(), "person_id={};ticket_number={}.2.jpg".format(person_id, ticket_number))
        opener.save_screenshot(filepath_canceled_ticket)

        # step 3
        opener.find_element_by_name("agree").click()
        opener.find_element_by_name("SubmitButton").click()
        filepath_canceled_ticket = os.path.join(thsr_cancel_dir(), "person_id={};ticket_number={}.3.jpg".format(person_id, ticket_number))
        opener.save_screenshot(filepath_canceled_ticket)

        # check successful or not
        try:
            title = opener.find_element_by_xpath("//td[@class='payment_title']").text
            if title == u"取消訂位成功！":
                filepath_canceled_ticket = os.path.join(thsr_cancel_dir(), "person_id={};ticket_number={}.4.jpg".format(person_id, ticket_number))
                opener.save_screenshot(filepath_canceled_ticket)

                is_cancelled = True
                retry = -1

                break
        except NoSuchElementException as nee:
            pass

        retry -= 1

    opener.quit()

    return is_cancelled

if __name__ == "__main__":
    '''
    testing_params = {"booking_type": "general",
                      "person_id": "L122760167",
                      "cellphone": "0921747196",
                      "booking_date": "2017/03/01",
                      "booking_stime": "10:00",
                      "booking_etime": "12:00",
                      "selectStartStation": "桃園",
                      "selectDestinationStation": "台中",
                      "preferred_seat": "seatRadio1",
                      "booking": "bookingMethod1",
                      "onlyQueryOffPeakCheckBox": True,
                      "ticketPanel:rows:0:ticketAmount": 1,
                      "ticketPanel:rows:1:ticketAmount": 0}
    '''
    testing_params = {"booking_type": "student",
                      "person_id": "L122760167",
                      "ticketPanel:rows:1:ticketAmount": 0,
                      "booking": "bookingMethod1",
                      "onlyQueryOffPeakCheckBox": False,
                      "booking_stime": "07:00",
                      "booking_date": "2017/03/03",
                      "cellphone": "0921747196",
                      "selectDestinationStation": "台中",
                      "preferred_seat": "seatRadio1",
                      "booking_etime": "12:00",
                      "selectStartStation": "桃園",
                      "ticketPanel:rows:0:ticketAmount": 2,
                      "ticketPanel:rows:4:ticketAmount": 1}

    print book_ticket(testing_params, cropped=2, driver="chrome")
    #cancel_ticket(person_id="L122760167", ticket_number="06038429")
