#!/usr/bin/env python

import os
import time
import random

from PIL import Image

from lib.ocr.cracker import init_model, crack_tra
from lib.ocr.utils import get_digest
from lib.common.utils import get_chrome_driver, get_phantom_driver, log
from lib.ticket.utils import URL_TRA, URL_TRAINNO_TRA
from lib.ticket.utils import tra_img_dir, tra_screen_dir, tra_success_dir, tra_fail_dir, tra_ticket_dir

from selenium.common.exceptions import NoSuchElementException

init_model("tra")

def book_ticket(param, cropped=1, driver="phantom"):
    web_opener = None
    if driver == "chrome":
        web_opener = get_chrome_driver()
    else:
        web_opener = get_phantom_driver()

    is_time = param.get("train_no", None) is None

    retry = 2
    train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time= None, None, None, None, None, None, None, None

    ticket_number, ticket_filepath = None, None
    while retry >= 0:
        tickets = []

        if is_time:
            web_opener.get(URL_TRA)
        else:
            web_opener.get(URL_TRAINNO_TRA)

        for key, value in param.items():
            if isinstance(value, (str, unicode)):
                try:
                    element = web_opener.find_element_by_id(key)
                    element.send_keys(param[key])
                except NoSuchElementException as e:
                    pass

        web_opener.find_element_by_xpath("//button[@type='submit']").click()
        time.sleep(random.randint(2, 3))

        img = web_opener.find_element_by_xpath("//img[@id='idRandomPic']")
        location = img.location
        size = img.size

        filepath_screenshot = os.path.join(tra_screen_dir(), "{}.jpg".format(int(time.time()*1000)))
        web_opener.save_screenshot(filepath_screenshot)
        log("save the screenshot in {}".format(filepath_screenshot))

        im = Image.open(filepath_screenshot)

        if driver == "chrome":
            im = im.resize((im.size[0]/2, im.size[1]/2), Image.ANTIALIAS)

        im = im.crop((location["x"], location["y"], location["x"]+size["width"], location["y"] + size["height"]))

        im_filepath = os.path.join(tra_img_dir(), "{}.jpg".format(get_digest(im)))
        im.save(im_filepath)
        log("save the cropped image in {}".format(im_filepath))

        answer = crack_tra(im_filepath, cropped, basefolder=os.path.join(tra_img_dir(), ".."))
        web_opener.find_element_by_id("randInput").send_keys(answer)
        log("for {}, the predicted input is {}".format(im_filepath, answer))

        web_opener.find_element_by_xpath("//button[@type='submit']").click()
        web_opener.save_screenshot("/tmp/{}.jpg".format(retry))
        time.sleep(random.randint(1, 3))

        if is_time:
            for ticket in web_opener.find_elements_by_tag_name("a"):
                url = ticket.get_attribute("href")
                if url.find("check_ctno1.jsp") > -1:
                    for e in web_opener.find_elements_by_xpath("//tr[@class='gray01 text_10p']"):
                        info = e.text.split()
                        train_number, train_type, start_date, start_time, start_station, end_station, end_date, end_time = info[:8]

                        break

                    ticket.click()
                    time.sleep(random.randint(1, 5))

                    destination = os.path.join(tra_success_dir(), os.path.basename(im_filepath))
                    os.rename(im_filepath, destination)

                    ticket_number = web_opener.find_element_by_xpath("//span[@class='hv1 red02 text_14p bold01']").text
                    param["ticket"] = ticket_number

                    ticket_filepath = os.path.join(tra_ticket_dir(), "id={}_ticket={}.jpg".format(\
                        param["person_id"], param["ticket"]))
                    log("the filepath_ticket is {}".format(ticket_filepath))

                    web_opener.save_screenshot(ticket_filepath)

                    retry = -1

                    break
        else:
            try:
                ticket_number = web_opener.find_element_by_id("spanOrderCode").text

                elements = web_opener.find_elements_by_xpath("//span[@class=\"hv1 blue01 bold01\"]")

                train_number = elements[1].text
                train_type = elements[2].text
                start_date, start_time = elements[3].text.split(" ")
                start_station = elements[4].text
                end_station = elements[5].text
                end_date = "-"
                end_time = "-"

                retry = -1
            except NoSuchElementException as e:
                log(e)

                retry -= 1

        log("book the ticket number - {}".format(ticket_number))

        time.sleep(random.randint(1, 5))
        retry -= 1

    web_opener.quit()

    return ticket_number, ticket_filepath, (train_number, train_type, param["order_qty_str"], start_date, start_time, start_station, end_station, end_date, end_time)

if __name__ == "__main__":
    param = {'to_station': '185', 'tra_mode': 'time', 'getin_end_dtime': '23:00', 'getin_date': '2017/03/15-00', 'order_qty_str': '1', 'getin_start_dtime': '18:00', 'train_type': '*4', 'from_station': '175', 'person_id': 'L122760167'}

    #print book_ticket(param, driver="chrome")

    param = {'to_station': '115', 'tra_mode': 'train_no', 'train_no': '653', 'getin_date': '2017/04/01-00', 'order_qty_str': '1', 'from_station': '100', 'person_id': 'L122760167'}

    print book_ticket(param, driver="chrome")
