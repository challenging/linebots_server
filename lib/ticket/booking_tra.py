#!/usr/bin/env python

import io
import os
import sys
import time
import hashlib
import urllib
import random
import cStringIO

from bs4 import BeautifulSoup
from PIL import Image

from lib.ocr.cracker import crack
from lib.common.utils import get_chrome_driver, get_phantom_driver
from lib.ticket.utils import tra_img_dir, tra_screen_dir, tra_success_dir, tra_ticket_dir

encoder = hashlib.md5()

testing_params = {"person_id": "L122760167",
                  "getin_date": "2017/02/17-00",
                  "from_station": "106",
                  "to_station": "130",
                  "order_qty_str": "1",
                  "train_type": "*4",
                  "getin_start_dtime": "09:00",
                  "getin_end_dtime": "17:00"}

def book_ticket(param, cropped=1):
    global encoder

    retry = 2
    web_opener = get_phantom_driver()

    while retry >= 0:
        tickets = []

        web_opener.get("http://railway1.hinet.net/csearch.htm")

        for key, value in param.items():
            element = web_opener.find_element_by_id(key)
            element.send_keys(param[key])

        web_opener.find_element_by_xpath("//button[@type='submit']").click()

        img = web_opener.find_element_by_xpath("//img[@id='idRandomPic']")
        location = img.location
        size = img.size

        filepath_screenshot = os.path.join(tra_screen_dir(), "{}.png".format(int(time.time()*1000)))
        web_opener.save_screenshot(filepath_screenshot)
        print "save the screenshot in {}".format(filepath_screenshot)

        im = Image.open(filepath_screenshot)
        #im = im.resize((im.size[0]/2, im.size[1]/2), Image.ANTIALIAS)
        im = im.crop((location["x"], location["y"], location["x"]+size["width"], location["y"] + size["height"]))

        output = io.BytesIO()
        im.save(output, format='JPEG')
        encoder.update(output.getvalue())

        im_filepath = os.path.join(tra_img_dir(), "{}.jpg".format(encoder.hexdigest()))
        im.save(im_filepath)
        print "save the cropped image in {}".format(im_filepath)

        answer = crack(im_filepath, cropped, basefolder=os.path.join(tra_img_dir(), ".."))
        web_opener.find_element_by_id("randInput").send_keys(answer)
        time.sleep(2)

        web_opener.find_element_by_xpath("//button[@type='submit']").click()
        time.sleep(2)

        for ticket in web_opener.find_elements_by_tag_name("a"):
            url = ticket.get_attribute("href")
            if url.find("check_ctno1.jsp") > -1:
                ticket.click()
                time.sleep(random.randint(1, 5))

                destination = os.path.join(tra_success_dir(), os.path.basename(im_filepath))
                os.rename(im_filepath, destination)

                ticket_number = web_opener.find_element_by_xpath("//span[@class='hv1 red02 text_14p bold01']")
                param["ticket"] = ticket_number.text
                print "get ticket number - {}".format(param["ticket"])

                filepath_ticket = os.path.join(tra_ticket_dir(), "id={}_ticket={}.png".format(\
                    param["person_id"], param["ticket"]))
                print "the filepath_ticket is {}".format(filepath_ticket)

                web_opener.save_screenshot(filepath_ticket)

                retry = -1

                break

        time.sleep(random.randint(1, 5))
        retry -= 1

    time.sleep(2)
    print "retry again({})".format(retry)

    web_opener.quit()

if __name__ == "__main__":
    book_ticket(testing_params)
