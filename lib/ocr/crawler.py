#!/usr/bin/env python

import io
import os
import time
import click
import urllib

from PIL import Image

from lib.common.utils import get_phantom_driver, get_chrome_driver, check_folder
from lib.ocr.utils import get_digest

def crawl_tra_imint(folder="crack"):
    basepath_img = os.path.join(os.path.dirname(__file__), "etc", "tra", folder, "source")
    check_folder(basepath_img, is_folder=True)

    retry = 512
    while retry > 0:
        urllib.urlretrieve("http://railway1.hinet.net/ImageOut.jsp;jsessionid=VMt6QoesgHAFxK8c4dRSb8HtC2F8O5KGem8UwEOrwe464dVyR6Ks!-170005252",\
            os.path.join(basepath_img, "{}.jpg".format(int(1000*time.time()))))

        retry -= 1

def crawl_thsr_imint(folder="train"):
    basepath = os.path.join(os.path.dirname(__file__), "etc", "thsr", "crack")
    basepath_screenshot = os.path.join(basepath, "screenshot")
    check_folder(basepath_screenshot)

    basepath_img = basepath_img = os.path.join(basepath, folder)
    check_folder(basepath_img)

    opener = get_phantom_driver()
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

@click.command()
@click.option("-c", "--company", type=click.Choice(["thsr", "tra"]))
@click.option("-b", "--batch", default=1)
def crawl(company, batch):
    while batch > 0:
        try:
            if company == "tra":
                crawl_tra_imint()
            elif company == "thsr":
                crawl_thsr_imint()
            else:
                raise NotImplementedError
        except Exception as e:
            print e
            time.sleep(60)

        batch -= 1

if __name__ == "__main__":
    crawl()
