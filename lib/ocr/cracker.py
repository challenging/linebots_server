#!/usr/bin/env python

import os
import sys
import glob
import click
import numpy as np

from lib.common.utils import check_folder

from lib.ocr.thsr.convert import crop
from lib.ocr.tra.convert import get_number_rects, crop_image
from lib.ocr.model import cnn_preprocess
from lib.ocr.utils import latest_Y, latest_model, image_l, data_dir, cracker_dir

model_tra = None

model_thsr = None
model_thsr_y = None

def init_model(company):
    global model_tra
    global model_thsr, model_thsr_y

    if company == "tra" and model_tra is None:
        model_tra = latest_model(model_tra, company)
    elif company == "thsr" and model_thsr is None:
        model_thsr = latest_model(model_thsr, company)
        model_thsr_y = latest_Y(company)

def crack_tra(input, basefolder=cracker_dir("tra"), pix_filter=128):
    global model_tra

    filename = os.path.basename(input)
    area = get_number_rects(input)

    folder = os.path.join(basefolder, "cropped", filename)
    check_folder(folder, is_folder=True)

    crop_image(input, area, folder, pix_filter)

    answer = ""
    scanned_files = os.path.join(folder, "*.jpg")
    for filepath in sorted(glob.glob(scanned_files), key=os.path.getctime):
        _, csgraph = image_l(filepath)
        dataset, _, _ = cnn_preprocess(np.array([csgraph]))

        c = str(np.argmax(model_tra.predict(dataset), axis=1)[0])
        if c != "10":
            answer += c

    return answer

def crack_thsr(input, basefolder=cracker_dir("thsr")):
    global model_thsr, model_thsr_y

    init_model("thsr")

    filename = os.path.basename(input)

    folder_cropped = os.path.join(basefolder, "cropped")
    check_folder(folder_cropped, is_folder=True)

    crop(input, folder_cropped)

    answer = ""
    scanned_files = os.path.join(basefolder, "cropped", filename, "*.jpg")
    for filepath in sorted(glob.glob(scanned_files), key=os.path.getctime):
        _, csgraph = image_l(filepath)
        dataset, _, _ = cnn_preprocess(np.array([csgraph]))

        answer += model_thsr_y[np.argmax(model_thsr.predict(dataset), axis=1)[0]]

    return answer

@click.command()
@click.option("-i", "--input")
@click.option("-c", "--company", type=click.Choice(["tra", "thsr"]))
def process(input, company):
    if input is None:
        print "Not found --input parameter"

        sys.exit(999)
    else:
        init_model(company)

    count_all, count_number, count_right = 0, 0, 0
    for input in glob.iglob(input):
        number = os.path.basename(input).split(".")[0]

        if company == "tra":
            answer = crack_tra(input)
        elif company == "thsr":
            answer = crack_thsr(input)

        mark_len = "x"
        if len(answer) == len(number):
            mark_len = "o"
            count_number += 1

        mark_correct = "-"
        if answer == number:
            mark_correct = "+"
            count_right += 1

        print "{}{} The prediction/real answer is {}/{}".format(mark_len, mark_correct, answer, number)

        count_all += 1

    print count_all, count_number, count_right
    print "The accuracy of predictions is {:.4f}% / {:.4f}%".format(count_right*100.0/count_all, count_right*100.0/count_number)

if __name__ == "__main__":
    process()
