#!/usr/bin/env python

import io
import os
import time
import hashlib

from PIL import Image

from lib.common.utils import get_phantom_driver, get_chrome_driver, check_folder
from lib.ocr.utils import get_digest

basepath = os.path.join(os.path.dirname(__file__), "etc", "thsr", "crack")
basepath_screenshot = os.path.join(basepath, "screenshot")
check_folder(basepath_screenshot)

def crawl_thsr_imint(folder="train"):
    global basepath, basepath_screenshot

    basepath_img = basepath_img = os.path.join(basepath, folder)
    check_folder(basepath_img)

    opener = get_phantom_driver()
    #opener = get_chrome_driver()
    opener.get("https://irs.thsrc.com.tw/IMINT/")

    retry = 512
    while retry > 0:
        time.sleep(4)

        filepath_screenshot = os.path.join(basepath_screenshot, "{}.jpg".format(retry))
        check_folder(filepath_screenshot, is_folder=False)
        opener.save_screenshot(filepath_screenshot)
        print "save the screenshot in {}".format(filepath_screenshot)

        img = opener.find_element_by_id("BookingS1Form_homeCaptcha_passCode")
        location, size = img.location, img.size

        im = Image.open(filepath_screenshot)
        #im = im.resize((im.size[0]/2, im.size[1]/2), Image.ANTIALIAS)
        im = im.crop((location["x"]+5, location["y"], location["x"]+size["width"]+5, location["y"] + size["height"]))

        im_filepath = os.path.join(basepath_img, "{}.jpg".format(get_digest(im)))
        check_folder(im_filepath)
        im.save(im_filepath)
        print "save the cropped image in {}".format(im_filepath)

        opener.find_element_by_id("BookingS1Form_homeCaptcha_reCodeLink").click()
        retry -= 1

    opener.quit()
    opener.close()

if __name__ == "__main__":
    while True:
        try:
            crawl_thsr_imint()
        except Exception as e:
            print e
            time.sleep(60)
