#!/usr/bin/env python

import os
import time
import random

from PIL import Image

from lib.ocr.cracker import crack_tra
from lib.common.utils import URL_TRA
from lib.common.utils import get_chrome_driver, get_phantom_driver, get_digest
from lib.ticket.utils import tra_img_dir, tra_screen_dir, tra_success_dir, tra_fail_dir, tra_ticket_dir

crack_tra.init_model("tra")

web_opener = get_phantom_driver()
def book_ticket(param, cropped=1):
    global web_opener

    retry = 2
    train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time= None, None, None, None, None, None, None, None

    ticket_number, ticket_filepath = None, None
    while retry >= 0:
        tickets = []

        web_opener.get(URL_TRA)

        for key, value in param.items():
            if isinstance(value, (str, unicode)):
                element = web_opener.find_element_by_id(key)
                element.send_keys(param[key])

        web_opener.find_element_by_xpath("//button[@type='submit']").click()

        img = web_opener.find_element_by_xpath("//img[@id='idRandomPic']")
        location = img.location
        size = img.size

        filepath_screenshot = os.path.join(tra_screen_dir(), "{}.jpg".format(int(time.time()*1000)))
        web_opener.save_screenshot(filepath_screenshot)
        print "save the screenshot in {}".format(filepath_screenshot)

        im = Image.open(filepath_screenshot)
        #im = im.resize((im.size[0]/2, im.size[1]/2), Image.ANTIALIAS)
        im = im.crop((location["x"], location["y"], location["x"]+size["width"], location["y"] + size["height"]))

        im_filepath = os.path.join(tra_img_dir(), "{}.jpg".format(get_digest(im)))
        im.save(im_filepath)
        print "save the cropped image in {}".format(im_filepath)

        answer = crack_tra(im_filepath, cropped, basefolder=os.path.join(tra_img_dir(), ".."))
        web_opener.find_element_by_id("randInput").send_keys(answer)
        print "for {}, the predicted input is {}".format(im_filepath, answer)
        time.sleep(2)

        web_opener.find_element_by_xpath("//button[@type='submit']").click()
        web_opener.save_screenshot("/tmp/{}.jpg".format(retry))
        time.sleep(5)

        for ticket in web_opener.find_elements_by_tag_name("a"):
            url = ticket.get_attribute("href")
            if url.find("check_ctno1.jsp") > -1:
                for e in web_opener.find_elements_by_xpath("//tr[@class='gray01 text_10p']"):
                    train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time = e.text.split()

                    break

                ticket.click()
                time.sleep(random.randint(1, 5))

                destination = os.path.join(tra_success_dir(), os.path.basename(im_filepath))
                os.rename(im_filepath, destination)

                ticket_number = web_opener.find_element_by_xpath("//span[@class='hv1 red02 text_14p bold01']").text
                param["ticket"] = ticket_number
                print "get ticket number - {}".format(param["ticket"])

                ticket_filepath = os.path.join(tra_ticket_dir(), "id={}_ticket={}.jpg".format(\
                    param["person_id"], param["ticket"]))
                print "the filepath_ticket is {}".format(ticket_filepath)

                web_opener.save_screenshot(ticket_filepath)

                retry = -1

                break

        print "book the ticket number - {}".format(ticket_number)

        time.sleep(random.randint(1, 5))
        retry -= 1

    time.sleep(2)

    return ticket_number, ticket_filepath, (train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time)

if __name__ == "__main__":
    testing_params = {"person_id": "L122760167",
                  "getin_date": "2017/02/17-00",
                  "from_station": "106",
                  "to_station": "130",
                  "order_qty_str": "1",
                  "train_type": "*4",
                  "getin_start_dtime": "09:00",
                  "getin_end_dtime": "17:00"}

    print book_ticket(testing_params)
