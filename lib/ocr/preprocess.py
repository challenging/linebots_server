#!/usr/bin/env python

import os
import sys
import glob
import click
import shutil
import numpy as np

from lib.common.utils import check_folder
from lib.ocr.utils import image_l, data_dir, get_digest

def copy_image_to_number_folder(data_input, data_output):
    for idx, filepath in enumerate(glob.iglob(os.path.join(data_input, "*", "*", "*.jpg"))):
        filename = os.path.basename(filepath)
        _, n, _ = filename.split(".")

        destination_folder = os.path.join(data_output, str(n))
        check_folder(destination_folder, is_folder=True)

        im, csgraph = image_l(filepath)
        digest = get_digest(im)
        with open(os.path.join(destination_folder, "{}.npy".format(digest)), "wb") as out_file:
            np.save(out_file, csgraph)

        shutil.copy(filepath, os.path.join(destination_folder, "{}.jpg".format(digest)))

@click.command()
@click.option("-i", "--input")
@click.option("-c", "--company", type=click.Choice(["tra", "thsr"]))
def main(input, company):
    data_input = os.path.join(data_dir(), company, "train", input)
    data_output = os.path.join(data_dir(), company, "train", "number")

    copy_image_to_number_folder(data_input, data_output)

if __name__ == "__main__":
    main()
