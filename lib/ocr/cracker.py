#!/usr/bin/env python

import os
import sys
import glob
import click
import numpy as np

from convert import convert_wb_1, convert_wb_2, crop_component, detect_connected_component
from model import cnn_preprocess
from utils import latest_model, image_l, data_dir, cracker_dir

model = None
if model is None:
    model = latest_model(model)

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
        filename = os.path.basename(input)
        number = filename.split(".")[0]

        filepath_wb_1, _ = convert_wb_1(input)
        filepath_wb_2, graph = convert_wb_2(filepath_wb_1)
        area = detect_connected_component(graph)

        f = None
        if cropped == "1":
            f = filepath_wb_1
        elif cropped == "2":
            f = filepath_wb_2
        else:
            print "Not support cropped={}".format(cropped)

            sys.exit(999)

        folder = os.path.basename(os.path.dirname(f))
        crop_component(f, area, folder="cropped_{}".format(folder))

        answer = ""
        for filepath in glob.iglob(os.path.join(cracker_dir(), "cropped_{}".format(folder), filename, "*.jpg")):
            _, csgraph = image_l(filepath)
            dataset, _, _ = cnn_preprocess(np.array([csgraph]))

            c = str(np.argmax(model.predict(dataset), axis=1)[0])
            if c != "10":
                answer += c

        print "{} - ({})The prediction/real answer is {}/{}".format(folder, "+" if answer == number else "-", answer, number)

        count_number += 1 if len(answer) == len(number) else 0
        count_right += 1 if answer == number else 0
        count_all += 1

    print count_all, count_number, count_right
    print "The accuracy of predictions is {:.4f}% / {:.4f}%".format(count_right*100.0/count_all, count_right*100.0/count_number)

if __name__ == "__main__":
    process()
