#!/usr/bin/env python

import os
import glob
import click
import numpy as np
import scipy

from scipy import ndimage
from scipy.ndimage.measurements import label
from PIL import Image, ImageFilter, ImageEnhance

from utils import check_folder, image_l, data_dir

BOLD = 4
MARGIN = 2
OVERLAP = 0.16
WIDTH, HEIGHT = 26, 32

get_number = lambda filepath: os.path.basename(filepath).split(".")[0]
cal_rect = lambda rect: (float(rect[1]) - float(rect[0])) * (float(rect[3]) - float(rect[2]))

debug = False
messages = []
def log():
    global debug, messages

    if debug:
        print "\n".join([str(m) for m in messages])

    messages = []

def create_folders(type):
    for sub_folder in ["cropped", "convert_wb_1", "convert_wb_2"]:
        folder = os.path.join(data_dir(), type, sub_folder)
        check_folder(folder, is_folder=True)

def crop_component(filepath_input, area, folder="cropped"):
    global WIDTH, HEIGHT

    count = 0
    number = get_number(filepath_input)

    filename = os.path.basename(filepath_input)
    folder = os.path.join(os.path.dirname(filepath_input), "..", folder, filename)
    check_folder(folder, is_folder=True)

    im = Image.open(filepath_input)
    width, height = im.size[0], im.size[1]
    for idx, (top, bottom, left, right) in enumerate(area):
        n = "x"
        try:
            n = number[idx]
        except IndexError as e:
            pass

        filepath_output = os.path.join(folder, "{}.{}.jpg".format(idx+1, n))
        is_create_new_image = False

        w, h = right - left, bottom - top
        if w < WIDTH:
            shift_left = (WIDTH-w)/2
            shift_right = WIDTH - w - shift_left

            if left-shift_left > 0:
                left -= shift_left
            else:
                is_create_new_image = True

            if right+shift_right < width:
                right += shift_right
            else:
                is_create_new_image = True
        else:
            shift_left = (w-WIDTH)/2
            shift_right = w - WIDTH - shift_left

            left += shift_left
            right -= shift_right

        if h < HEIGHT:
            shift_top = (HEIGHT-h)/2
            shift_bottom = HEIGHT - h - shift_top

            if top-shift_top > 0:
                top -= shift_top
            else:
                is_create_new_image = True

            if bottom+shift_bottom < height:
                bottom += shift_bottom
            else:
                is_create_new_image = True
        else:
            shift_top = (h-HEIGHT)/2
            shift_bottom = h-HEIGHT-shift_top

            top += shift_top
            bottom -= shift_bottom

        check_folder(filepath_output)
        crop_im = im.crop((left, top, right, bottom))
        if is_create_new_image:
            size = (WIDTH, HEIGHT)

            layer = Image.new('L', size, (255))
            layer.paste(crop_im, tuple(map(lambda x:(x[0]-x[1])/2, zip(size, crop_im.size))))

            layer.save(filepath_output)
        else:
            if crop_im.size[0] != WIDTH or crop_im.size[1] != HEIGHT:
                print filename, right, left, bottom, top, crop_im.size

            crop_im.save(filepath_output)

        count += 1

    return count

def detect_connected_component(graph):
    global BOLD, MARGIN, OVERLAP
    global messages

    h, w = graph.shape
    messages.append("The (width, height) is ({}, {})".format(w, h))
    area = []

    blobs, number_of_blobs = label(graph)

    new_graph = blobs.ravel()
    unique_values, counts = np.unique(blobs, return_counts=True)
    for v, count in zip(unique_values, counts):
        pos = np.where(blobs[:,:] == v)
        x, y = pos[0], pos[1]
        top, bottom = x.min(), x.max()
        left, right = y.min(), y.max()

        if h-bottom < MARGIN or top < MARGIN or w-right < MARGIN:# the rect is closed bottom or top, just ignore it
            new_graph[new_graph == v] = 0
            messages.append("ignore {} because of {}".format((top, bottom, left, right), (h-bottom, w-right)))
        else: # just handle the foreground
            vv = 1

            if count < 32:
                vv = 0
                # TODO: should merge the closed rect area, ex., 06379, 70433, 112019
            else:
                top, bottom = max(0, top-BOLD*2), min(h, bottom+BOLD*2)
                left, right = max(0, left-BOLD), min(w, right+BOLD)

                area.append([top, bottom, left, right, count])
                messages.append("The rect is located at {}".format((top, bottom, left, right)))

            new_graph[new_graph == v] = vv

    for line in new_graph.reshape(h, w):
        messages.append("".join([str(v) for v in line]))

    # sort the rect from left to right
    area = sorted(area, key=lambda e: e[2])

    # check the overlapping of rect
    idx = 0
    removed_idx = []
    while idx < len(area)-1:
        this = area[idx]
        next = area[idx+1]

        u_left, u_right, u_top, u_bottom = min(this[2], next[2]), max(this[3], next[3]), min(this[0], next[0]), max(this[1], next[1])
        if this[3] >= next[2] and this[1] >= next[0]:
            i_left, i_right, i_top, i_bottom = min(this[3], next[2]), max(this[3], next[2]), min(this[1], next[0]), max(this[0], next[1])

            u_rect, i_rect = cal_rect((u_left, u_right, u_top, u_bottom)), cal_rect((i_left, i_right, i_top, i_bottom))

            ratio = i_rect / u_rect
            if ratio >= OVERLAP:
                if this[4] > next[4]:
                    removed_idx.append((idx+1, (this, next), ratio))
                else:
                    removed_idx.append((idx, (this, next), ratio))

                idx += 1

        idx += 1

    for idx in range(len(area)):
        area[idx] = area[idx][0:4]

    for idx, rects, ratio in reversed(removed_idx):
        del area[idx]

    log()

    return area

def convert_wb_2(filepath_input, folder="convert_wb_2"):
    global messages

    im, _ = image_l(filepath_input)

    filepath_output = os.path.join(os.path.dirname(filepath_input), "..", folder, os.path.basename(filepath_input))
    check_folder(filepath_output)
    im.save(filepath_output)

    messages.append(os.path.basename(filepath_input))

    csgraph = []
    pixdata = im.load()
    for y in xrange(im.size[1]):
        line = []
        for x in xrange(im.size[0]):
            v = 0 if pixdata[x, y] > 0 else 1
            line.append(v)

        csgraph.append(line)
        messages.append("".join(str(v) for v in line))

    messages.append("\n")
    log()

    return filepath_output, np.array(csgraph)

def convert_wb_1(filepath_input, folder="convert_wb_1"):
    img = Image.open(filepath_input)
    img = img.convert("RGBA")

    pixdata = img.load()

    # Make the letters bolder for easier recognition
    for y in xrange(img.size[1]):
        for x in xrange(img.size[0]):
            if pixdata[x, y][0] < 90:
                pixdata[x, y] = (0, 0, 0, 255)

    for y in xrange(img.size[1]):
        for x in xrange(img.size[0]):
            if pixdata[x, y][1] < 136:
                pixdata[x, y] = (0, 0, 0, 255)

    for y in xrange(img.size[1]):
        for x in xrange(img.size[0]):
            if pixdata[x, y][2] > 0:
                pixdata[x, y] = (255, 255, 255, 255)

    filepath_output = os.path.join(os.path.dirname(filepath_input), "..", folder, os.path.basename(filepath_input))
    check_folder(filepath_output)
    img.save(filepath_output)

    return filepath_output

@click.command()
@click.option("-t", "--type", type=click.Choice(["train", "test"]))
@click.option("-v", "--vvv", is_flag=True)
def main(type, vvv):
    global debug
    debug = vvv

    folder = os.path.join(data_dir(), type)
    create_folders(type)

    total_crop, accuracy_crop, wrong_crop = 0, 0, []

    if vvv and type == "train":
        files = ["004801.jpg", "06379.jpg", "70433.jpg", "872360.jpg", "208202.jpg", "357559.jpg", "12018.jpg", "112019.jpg", "984017.jpg"]
        files = [os.path.join(folder, filename) for filename in files]
    else:
        files = glob.iglob("{}/source/*.jpg".format(folder))

    for filepath in files:
        number = get_number(filepath)

        if os.path.isfile(filepath):
            filepath_wb_2, graph = convert_wb_2(convert_wb_1(filepath))
            area = detect_connected_component(graph)

            if crop_component(filepath_wb_2, area) == len(number):
                accuracy_crop += 1
            else:
                wrong_crop.append(number)

            total_crop += 1

    print "The accuracy of cropped image is {} / {} = {:.2f}%".format(accuracy_crop, total_crop, accuracy_crop*100.0/total_crop)
    print "The wrong number of cropped image are {}".format(",".join(wrong_crop))

if __name__ == "__main__":
    main()
