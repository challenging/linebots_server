#!/usr/bin/env python

import os
import sys
import glob
import click
import shutil
import numpy as np

from utils import image_l

basepath_data_input = os.path.join(os.path.dirname(__file__), "etc", "train", "cropped")
basepath_data_output = os.path.join(os.path.dirname(__file__), "etc", "train", "number")

def copy_image_to_number_folder():
    global basepath_data_input, basepath_data_output

    part = {}
    for filepath in glob.iglob(os.path.join(basepath_data_input, "*", "*.jpg")):
        filename = os.path.basename(filepath)
        idx, n, _ = filename.split(".")

        part.setdefault(n, 0)
        part[n] += 1

        destination_folder = os.path.join(basepath_data_output, str(n))
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        _, cs_graph = image_l(filepath)
        with open(os.path.join(destination_folder, "{}.npy".format(part[n])), "wb") as in_file:
            np.save(in_file, csgraph)

        shutil.copy(filepath, os.path.join(destination_folder, "{}.jpg".format(part[n])))

@click.command()
def main():
    global basepath_data_input, basepath_data_output

    for type in ["train", "test"]:
        basepath_data_input = os.path.join(os.path.dirname(__file__), "etc", type, "cropped")
        basepath_data_output = os.path.join(os.path.dirname(__file__), "etc", type, "number")

        copy_image_to_number_folder()

if __name__ == "__main__":
    main()
