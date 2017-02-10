#!/usr/bin/env python

import os
import sys
import glob
import click
import numpy as np

from lib.common.utils import check_folder

from lib.ocr.thsr.convert import crop
from lib.ocr.convert import convert_wb_1, convert_wb_2, crop_component, detect_connected_component
from lib.ocr.model import cnn_preprocess
from lib.ocr.utils import latest_Y, latest_model, image_l, data_dir, cracker_dir

model = None
Y = None

def init_model(company):
    global model, Y

    if model is None:
        model = latest_model(model, company)

    if company == "thsr":
        Y = latest_Y(company)

def crack_tra(input, cropped, basefolder=cracker_dir("tra")):
    global model

    filename = os.path.basename(input)

    filepath_wb_1, _ = convert_wb_1(input)
    filepath_wb_2, graph = convert_wb_2(filepath_wb_1)
    area = detect_connected_component(graph)

    f = filepath_wb_1
    if cropped == "2":
        f = filepath_wb_2

    folder = os.path.basename(os.path.dirname(f))
    crop_component(f, area, folder="cropped_{}".format(folder))

    answer = ""
    scanned_files = os.path.join(basefolder, "cropped_{}".format(folder), filename, "*.jpg")
    for filepath in sorted(glob.glob(scanned_files), key=os.path.getctime):
        _, csgraph = image_l(filepath)
        dataset, _, _ = cnn_preprocess(np.array([csgraph]))

        c = str(np.argmax(model.predict(dataset), axis=1)[0])
        if c != "10":
            answer += c

    return answer

def crack_thsr(input, cropped, basefolder=cracker_dir("thsr")):
    global model, Y

    init_model("thsr")

    filename = os.path.basename(input)

    folder_cropped_1 = os.path.join(basefolder, "cropped_1")
    folder_cropped_2 = os.path.join(basefolder, "cropped_2")
    for f in [folder_cropped_1, folder_cropped_2]:
        check_folder(f, is_folder=True)

    crop(input, folder_cropped_1, folder_cropped_2)

    answer = ""
    scanned_files = os.path.join(basefolder, "cropped_{}".format(cropped), filename, "*.jpg")
    for filepath in sorted(glob.glob(scanned_files), key=os.path.getctime):
        _, csgraph = image_l(filepath)
        dataset, _, _ = cnn_preprocess(np.array([csgraph]))

        answer += Y[np.argmax(model.predict(dataset), axis=1)[0]]

    return answer

@click.command()
@click.option("-i", "--input")
@click.option("-c", "--company", type=click.Choice(["tra", "thsr"]))
@click.option("-t", "--type", type=click.Choice(["1", "2"]))
def process(input, company, type):
    global model

    if input is None:
        print "Not found --input parameter"

        sys.exit(999)
    else:
        init_model(company)

    count_all, count_number, count_right = 0, 0, 0
    for input in glob.iglob(input):
        number = os.path.basename(input).split(".")[0]

        if company == "tra":
            answer = crack_tra(input, type)
        elif company == "thsr":
            answer = crack_thsr(input, type)

        mark_len = "x"
        if len(answer) == len(number):
            mark_len = "o"
            count_number += 1

        mark_correct = "-"
        if answer == number:
            mark_correct = "+"
            count_right += 1

        print "[{}]. {}{} The prediction/real answer is {}/{}".format(type, mark_len, mark_correct, answer, number)

        count_all += 1

    print count_all, count_number, count_right
    print "The accuracy of predictions is {:.4f}% / {:.4f}%".format(count_right*100.0/count_all, count_right*100.0/count_number)

if __name__ == "__main__":
    process()
