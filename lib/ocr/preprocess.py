#!/usr/bin/env python

import os
import sys
import time
import glob
import click
import shutil
import numpy as np

from utils import image_l, data_dir, check_folder

def copy_image_to_number_folder(data_input, data_output):
    timestamp = int(time.time())
    for idx, filepath in enumerate(glob.iglob(os.path.join(data_input, "*", "*.jpg"))):
        filename = os.path.basename(filepath)
        _, n, _ = filename.split(".")

        key = "{}_{}".format(timestamp, idx)

        destination_folder = os.path.join(data_output, str(n))
        check_folder(destination_folder, is_folder=True)

        _, csgraph = image_l(filepath)
        with open(os.path.join(destination_folder, "{}.npy".format(key)), "wb") as in_file:
            np.save(in_file, csgraph)

        shutil.copy(filepath, os.path.join(destination_folder, "{}.jpg".format(key)))

@click.command()
@click.option("-i", "--input")
def main(input):
    if input is None:
        print "Not found input parameter"
    else:
        data_input = os.path.join(data_dir(), "test", input)
        data_output = os.path.join(data_dir(), "test", "number")

        copy_image_to_number_folder(data_input, data_output)

if __name__ == "__main__":
    main()
