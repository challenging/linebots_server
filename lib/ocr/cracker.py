#!/usr/bin/env python

import os
import sys
import glob
import click
import numpy as np

from convert import convert_wb_1, convert_wb_2, crop_component, detect_connected_component
from model import cnn_preprocess
from utils import latest_model, image_l, data_dir, cracker_dir

basepath_cracker_cropped = os.path.join(cracker_dir(), "cropped")

model = None
if model is None:
    model = latest_model(model)

@click.command()
@click.option("-i", "--input")
def process(input):
    global model

    if input is None:
        print "Not found --input parameter"

        sys.exit(999)
    else:
        if not os.path.exists(input):
            print "Not found input file({})".format(input)

            sys.exit(998)

    filename = os.path.basename(input)

    filepath_wb_2, graph = convert_wb_2(convert_wb_1(input))
    count_number = crop_component(filepath_wb_2, detect_connected_component(graph))

    answer = ""
    for filepath in glob.iglob(os.path.join(basepath_cracker_cropped, filename, "*.jpg")):
        idx, _, _ = os.path.basename(filepath).split(".")

        _, csgraph = image_l(filepath)
        dataset, _, _ = cnn_preprocess(np.array([csgraph]))

        answer += str(np.argmax(model.predict(dataset), axis=1)[0])

    print "The prediction answer is {}".format(answer)

if __name__ == "__main__":
    process()
