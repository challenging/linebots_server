#!/usr/bin/env python

import os
import glob
import click
import numpy as np

from scipy.ndimage.measurements import label
from PIL import Image, ImageDraw

from lib.common.utils import check_folder
from lib.ocr.utils import image_l, data_dir, get_connected_components, calculate_rect_gap, downgrade_image, downgrade_image_l, get_cropped_rects

BOLD = 4
MARGIN = 4
WIDTH, HEIGHT = 32, 32

get_number = lambda filepath: os.path.basename(filepath).split(".")[0]

def crop_image(filepath_input, rects, folder, pix_filters=[110, 128, 156]):
    global WIDTH, HEIGHT, BOLD
    size = (WIDTH, HEIGHT)

    is_create_pix_filter = True
    if isinstance(pix_filters, int):
        is_create_pix_filter = False
        pix_filters = [pix_filters]

    for pix_filter in pix_filters:
        img = Image.open(filepath_input)
        downgrade_image_l(img, pix_filter)

        numbers = get_number(filepath_input).split(".")[0]
        filepath_output = os.path.join(os.path.dirname(filepath_input), "..", folder, os.path.basename(filepath_input))
        check_folder(filepath_output)

        for idx, rect in enumerate(rects):
            cropped_im = img.crop(rect)

            layer = Image.new('1', size, (255))
            layer.paste(cropped_im, tuple(map(lambda x:(x[0]-x[1])/2, zip(size, cropped_im.size))))

            n = "x"
            if idx < len(numbers):
                n = numbers[idx]

            filepath_output = None
            if is_create_pix_filter:
                filepath_output = os.path.join(folder, str(pix_filter), "{}.{}.jpg".format(idx+1, n))
            else:
                filepath_output = os.path.join(folder, "{}.{}.jpg".format(idx+1, n))

            check_folder(filepath_output)

            layer.save(filepath_output)

def insert_imaged_rect(tmp_pix_filter, tmp_cluster_filter, tmp_img, cropped_rects, shift):
    global BOLD

    while tmp_pix_filter > 10 and tmp_cluster_filter > 10:
        rects = get_connected_components(downgrade_image(tmp_img, tmp_pix_filter), tmp_cluster_filter)
        tmp_cropped_rects = get_cropped_rects(rects, tmp_img.size[0], tmp_img.size[1], BOLD)
        tmp_cropped_rects.reverse()

        for r in tmp_cropped_rects:
            moved_r = (r[0]+shift[0], r[1]+shift[1], r[2]+shift[0], r[3]+shift[1])
            cropped_rects.insert(0, moved_r)

            tmp_pix_filter, tmp_cluster_filter = -1, -1

        tmp_pix_filter -= 10
        tmp_cluster_filter -= 10

    return sorted(cropped_rects, key=lambda x: x[0])

def get_number_rects(filepath_input, pix_filter=110, cluster_filter=36, threshold=(12, 28)):
    global BOLD, MARGIN

    im = Image.open(filepath_input)
    img = im.convert("RGB")
    width, height = img.size

    g = downgrade_image(img, pix_filter)
    rects = get_connected_components(g, cluster_filter)
    cropped_rects = get_cropped_rects(rects, width, height, BOLD)

    pos_first = cropped_rects[0]
    if pos_first > threshold[1]:
        tmp_pix_filter, tmp_cluster_filter = pix_filter+18, cluster_filter
        tmp_img = img.crop((0, 0, pos_first[0]-BOLD, height))
        cropped_rects = insert_imaged_rect(tmp_pix_filter, tmp_cluster_filter, tmp_img, cropped_rects, (0, 0))

    pos_last = cropped_rects[-1]
    if width-pos_last[2] > threshold[1]:
        tmp_pix_filter, tmp_cluster_filter = pix_filter+18, cluster_filter
        tmp_img = img.crop((pos_last[2]+BOLD, 0, width, height))
        cropped_rects = insert_imaged_rect(tmp_pix_filter, tmp_cluster_filter, tmp_img, cropped_rects, (pos_last[2]+BOLD, 0))

    cal_rect_area = lambda x: (x[2]-x[0])*(x[3]-x[1])
    cal_all_area = lambda x, y: cal_rect_area((min(x[0], y[0]), min(x[1], y[1]), max(x[2], y[2]), max(x[3], y[3])))

    idxs = []
    for idx in range(len(cropped_rects)-1):
        curr_area = cal_rect_area(cropped_rects[idx])
        next_area = cal_rect_area(cropped_rects[idx+1])
        all_area = cal_all_area(cropped_rects[idx], cropped_rects[idx+1])
        ratio = float(curr_area+next_area)/all_area

        if ratio > 0.975:
            idxs.append(idx)

    idxs.reverse()
    for idx in idxs:
        curr_rect = cropped_rects[idx]
        next_rect = cropped_rects[idx+1]

        cropped_rects[idx] = min(curr_rect[0], next_rect[0]), min(curr_rect[1], next_rect[1]), max(curr_rect[2], next_rect[2]), max(curr_rect[3], next_rect[3])
        del cropped_rects[idx+1]

    idxs = []
    for idx in range(len(cropped_rects)):
        w = cropped_rects[idx][2]-cropped_rects[idx][0]
        if w > 34:
            idxs.append((idx, w/2))

    for idx, w in idxs:
        origin_right = cropped_rects[idx][2]
        cropped_rects[idx] = (cropped_rects[idx][0], cropped_rects[idx][1], cropped_rects[idx][0]+w, cropped_rects[idx][3])
        cropped_rects.insert(idx+1, (cropped_rects[idx][0]+w, cropped_rects[idx][1], origin_right, cropped_rects[idx][3]))

    idxs = []
    pre_right = -1
    for idx in range(len(cropped_rects)):
        if pre_right != -1:
            w = cropped_rects[idx][0] - pre_right
            if w >= threshold[1]:
                idxs.append(idx)

        pre_right = cropped_rects[idx][2]

    idxs.reverse()
    for idx in idxs:
        tmp_pix_filter, tmp_cluster_filter = pix_filter+18, cluster_filter
        tmp_img = img.crop((cropped_rects[idx-1][2]+BOLD, 0, cropped_rects[idx][0]-BOLD, height))
        #tmp_img.show()
        cropped_rects = insert_imaged_rect(tmp_pix_filter, tmp_cluster_filter, tmp_img, cropped_rects, (cropped_rects[idx-1][2]+BOLD, 0))

    for idx in range(len(cropped_rects)):
        cropped_rects[idx] = (max(0, cropped_rects[idx][0]-MARGIN), max(0, cropped_rects[idx][1]-MARGIN),
                              min(width, cropped_rects[idx][2]+MARGIN), min(height, cropped_rects[idx][3]+MARGIN))

    '''
    dr = ImageDraw.Draw(img)
    for left, top, right, bottom in cropped_rects:
        dr.rectangle(((left, top),(right, bottom)), outline = "red")
    img.show()
    '''

    return cropped_rects

@click.command()
@click.option("-o", "--output")
def main(output):
    pix_filter = 110
    cluster_filter = 36

    folder = os.path.join(data_dir(), "tra", "train")
    check_folder(folder, is_folder=True)

    total_crop, accuracy_crop, wrong_crop = 0, 0, []
    files = glob.iglob(os.path.join(folder, "source", "*.jpg"))  # 765481.jpg # 39812.jpg # 075751.jpg # 006370.jpg, 023871

    normal, more, less = 0, 0, 0
    gaps = [[], [], []]
    for filepath in files:
        numbers = get_number(filepath)
        rects = get_number_rects(filepath, pix_filter, cluster_filter)  #110, 36
        gap = calculate_rect_gap(rects)
        if len(rects) == len(numbers):
            filepath_output = os.path.join(folder, output, numbers)
            crop_image(filepath, rects, filepath_output)

            gaps[0].append(max(gap))
            accuracy_crop += 1
        else:
            n = None
            if len(rects) > len(numbers):
                n = "b"

                gaps[1].append(max(gap))
                more += 1
            else:
                n = "s"

                gaps[2].append(max(gap))
                less += 1

            filepath_output = os.path.join(folder, "{}_{}".format(output, n), numbers)
            crop_image(filepath, rects, filepath_output)

            wrong_crop.append(numbers)

        total_crop += 1

    for c, gap in zip([normal, more, less], gaps):
        print np.mean(gap), np.std(gap), c

    print "The accuracy of cropped image is {} / {} = {:.2f}%".format(accuracy_crop, total_crop, accuracy_crop*100.0/total_crop)
    print "The wrong number of cropped image are {}".format(",".join(wrong_crop))

if __name__ == "__main__":
    main()
