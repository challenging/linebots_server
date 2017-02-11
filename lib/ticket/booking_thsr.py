#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import random

from PIL import Image

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from lib.ocr.cracker import init_model, crack_thsr
from lib.common.utils import UTF8
from lib.common.utils import check_folder, get_chrome_driver, get_phantom_driver, log
from lib.ocr.utils import get_digest
from lib.ticket.utils import get_thsr_url
from lib.ticket.utils import thsr_img_dir, thsr_screen_dir, thsr_success_dir, thsr_fail_dir, thsr_ticket_dir

init_model("thsr")

def book_ticket(param, cropped=2):
    opener = get_phantom_driver()

    retry, ticket_number = 2, None
    while retry >= 0:
        opener.get(get_thsr_url(param["booking_type"]))

        # choose started station
        opener.find_element_by_name("selectStartStation").send_keys(unicode(param["selectStartStation"], UTF8))
        # choose destination station
        opener.find_element_by_name("selectDestinationStation").send_keys(unicode(param["selectDestinationStation"], UTF8))
        # only show the early bird tickets
        if param["onlyQueryOffPeakCheckBox"]:
            opener.find_element_by_id("onlyQueryOffPeakCheckBox").click()

        # preferred seat
        opener.find_element_by_id(param["preferred_seat"])
        # preferred booking method
        opener.find_element_by_id(param["booking"])
        # preferred date
        input_field = opener.find_element_by_id('toTimeInputField')
        opener.execute_script("arguments[0].value = ''", input_field)
        input_field.send_keys(param["booking_date"])
        # preferred time
        opener.find_element_by_name("toTimeTable").send_keys(param["booking_time"])
        # ticket amount
        if param["ticketPanel:rows:0:ticketAmount"] != 1:
            opener.find_element_by_name("ticketPanel:rows:0:ticketAmount").send_keys(param["ticketPanel:rows:0:ticketAmount"])

        opener.find_element_by_name("ticketPanel:rows:1:ticketAmount").send_keys(param["ticketPanel:rows:1:ticketAmount"])

        retry_crack = 5
        while retry_crack > 0:
            try:
                img = opener.find_element_by_id("BookingS1Form_homeCaptcha_passCode")
                location, size = img.location, img.size

                if isinstance(opener, webdriver.Chrome):
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

                if isinstance(opener, webdriver.Chrome):
                    im = im.resize((im.size[0]/2, im.size[1]/2), Image.ANTIALIAS)

                im_filepath = os.path.join(thsr_img_dir(), "{}.jpg".format(get_digest(im)))
                check_folder(im_filepath)
                im.save(im_filepath)
                log("save cropped image in {}".format(im_filepath))

                answer = crack_thsr(im_filepath, cropped=2)

                submit = opener.find_element_by_name("homeCaptcha:securityCode")
                submit.clear()
                submit.send_keys(answer)

                opener.find_element_by_id("SubmitButton").click()

                try:
                    # go to the next step
                    opener.find_element_by_id("BookingS2Form")
                    retry_crack = -1

                    break
                except NoSuchElementException as nee:
                    pass
            except NoSuchElementException as nee:
                pass

            retry -= 1
            time.sleep(random.randint(1, 5))

        trains = []
        for field in opener.find_elements_by_xpath("//tr"):
            if field.get_attribute("onMouseOver"):
                trains.append(field.text.split())

            for img_field in field.find_elements_by_tag_name("img"):
                trains[-1].append(img_field.get_attribute("src"))

            for radio_field in field.find_elements_by_name("TrainQueryDataViewPanel:TrainGroup"):
                trains[-1].append(radio_field)

        trains[0][-1].click()
        opener.find_element_by_name("SubmitButton").click()
        time.sleep(random.randint(1, 3))

        ticket_info = opener.find_element_by_xpath("//table[@class='table_simple']")

        opener.find_element_by_id("idNumber").send_keys(param["person_id"])
        opener.find_element_by_id("mobileInputRadio").click()
        opener.find_element_by_id("mobilePhone").send_keys(param["cellphone"])
        opener.find_element_by_name("agree").click()
        opener.find_element_by_id("isSubmit").click()

        ticket_number = opener.find_element_by_xpath("//td[@class='content_key']")
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

    return ticket_number

if __name__ == "__main__":
    testing_params = {"booking_type": "general",
                      "person_id": "L122760167",
                      "cellphone": "0921747196",
                      "booking_date": "2017/03/01",
                      "booking_time": "130P",
                      "selectStartStation": "桃園",
                      "selectDestinationStation": "台中",
                      "preferred_seat": "seatRadio1",
                      "booking": "bookingMethod1",
                      "onlyQueryOffPeakCheckBox": True,
                      "ticketPanel:rows:0:ticketAmount": 1,
                      "ticketPanel:rows:1:ticketAmount": 0}

    print book_ticket(testing_params)
