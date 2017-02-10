import os
import sys
import glob

from PIL import Image, ImageFilter, ImageDraw

from lib.common.utils import check_folder
from lib.ocr.utils import get_digest, image_l

# fix random seed for reproducibility

REDIUS = 20

basepath = os.path.join(os.path.dirname(__file__), "..", "etc", "thsr", "train")
basepath_source = os.path.join(basepath, "source")
basepath_cropped_1 = os.path.join(basepath, "cropped_1")
basepath_cropped_2 = os.path.join(basepath, "cropped_2")

def crop(filepath, folder_cropped_1, folder_cropped_2):
    global SIZE, REDIUS

    filename = os.path.basename(filepath)
    words = filename.split(".")[0]

    for cropped_type, folder in enumerate([folder_cropped_1, folder_cropped_2]):
        folder_destination = os.path.join(folder, filename)
        check_folder(folder_destination, is_folder=True)

        im = Image.open(filepath)
        im = im.convert("L")
        w, h = im.size

        if cropped_type == 1:
            pixdata = im.load()
            for y in xrange(0, im.size[1]):
                for x in xrange(0, im.size[0]):
                    v = 1 if pixdata[x, y] < 100 else 0

                    pixdata[x, y] = 0 if v == 1 else 255
        else:
            im = im.filter(ImageFilter.MedianFilter(size=3))

        draw = ImageDraw.Draw(im)
        for part in range(1, 5):
            left, top, right, bottom = w*part/5-REDIUS/1.8, h/2-REDIUS, w*part/5+REDIUS, h/2+REDIUS
            #draw.ellipse((left, top, right, bottom), outline="red")

            cropped_im = im.crop((left, top, right, bottom))
            filepath_destination = os.path.join(folder_destination, "{}.{}.jpg".format(part, words[part-1]))
            cropped_im.save(filepath_destination)

def run():
    global basepath_source, basepath_cropped_1, basepath_cropped_2

    for folder in [basepath_cropped_1, basepath_cropped_2]:
        check_folder(folder, is_folder=True)

    for idx, filepath in enumerate(glob.glob(os.path.join(basepath_source, "*.jpg"))):
        crop(filepath, basepath_cropped_1, basepath_cropped_2)

if __name__ == "__main__":
    run()
