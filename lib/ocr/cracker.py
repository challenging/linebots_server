#!/usr/bin/env python

import os
import sys
import glob
import click
import numpy as np

from lib.common.utils import check_folder

from convert import convert_wb_1, convert_wb_2, crop_component, detect_connected_component
from model import cnn_preprocess
from utils import latest_model, image_l, data_dir, cracker_dir

model = None
if model is None:
    model = latest_model(model)

def crack(input, cropped, basefolder=cracker_dir()):
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
    for filepath in sorted(glob.glob(scanned_files), key=os.path.basename):
        _, csgraph = image_l(filepath)
        dataset, _, _ = cnn_preprocess(np.array([csgraph]))

        c = str(np.argmax(model.predict(dataset), axis=1)[0])
        if c != "10":
            answer += c

    return answer

@click.command()
@click.option("-i", "--input")
@click.option("-c", "--cropped", type=click.Choice(["1", "2"]))
def process(input, cropped):
    global model

    if input is None:
        print "Not found --input parameter"

        sys.exit(999)

    count_all, count_number, count_right = 0, 0, 0
    for input in glob.iglob(input):
        number = os.path.basename(input).split(".")[0]

        answer = crack(input, cropped)

        mark_len = "x"
        if len(answer) == len(number):
            mark_len = "o"
            count_number += 1

        mark_correct = "-"
        if answer == number:
            mark_correct = "+"
            count_right += 1

        print "[{}]. {}{} The prediction/real answer is {}/{}".format(cropped, mark_len, mark_correct, answer, number)

        count_all += 1

    print count_all, count_number, count_right
    print "The accuracy of predictions is {:.4f}% / {:.4f}%".format(count_right*100.0/count_all, count_right*100.0/count_number)

if __name__ == "__main__":
    process()
