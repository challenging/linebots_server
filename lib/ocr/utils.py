#!/usr/bin/env python

import os
import io
import sys
import hashlib
import pickle
import numpy as np

from lib.common.utils import check_folder
from keras.models import model_from_json
from PIL import Image, ImageFilter, ImageEnhance

encoder = hashlib.md5()

def data_dir():
    return os.path.join(os.path.dirname(__file__), "etc")

def model_dir(folder):
    return os.path.join(data_dir(), folder, "model")

def cracker_dir(folder):
    return os.path.join(data_dir(), folder, "cracker")

def get_digest(im):
    output = io.BytesIO()
    im.save(output, format='JPEG')
    encoder.update(output.getvalue())

    return encoder.hexdigest()

def image_l(filepath):
    im = Image.open(filepath)
    im = im.convert("L")
    im = im.filter(ImageFilter.MedianFilter())
    enhancer = ImageEnhance.Contrast(im)
    im = enhancer.enhance(2)

    csgraph = []
    pixdata = im.load()
    for y in xrange(im.size[1]):
        line = []
        for x in xrange(im.size[0]):
            line.append(pixdata[x, y])

        csgraph.append(line)

    csgraph = np.array(csgraph)

    return im, csgraph

def save(filepath_json, filepath_weight, model):
    check_folder(filepath_json, is_folder=False)

    # serialize model to JSON
    model_json = model.to_json()
    with open(filepath_json, "w") as json_file:
        json_file.write(model_json)

    # serialize weights to HDF5
    model.save_weights(filepath_weight)

    print("Saved model({}, {}) to disk".format(filepath_json, filepath_weight))

def load(filepath_json, filepath_weight, model):
    # load json and create model
    with open(filepath_json, 'r') as json_file:
        loaded_model_json = json_file.read()

        model = model_from_json(loaded_model_json)

    # load weights into new model
    model.load_weights(filepath_weight)

    return model

def latest_model(model, company="tra"):
    model_json = os.path.join(model_dir(company), "model.json")
    model_h5 = os.path.join(model_dir(company), "model.h5")

    if os.path.exists(model_json) and os.path.exists(model_h5):
        print "load_model from {}, {}".format(model_json, model_h5)
        return load(model_json, model_h5, model)
    else:
        print "Not found {}({}), {}({})".format(\
            model_json, os.path.exists(model_json), model_h5, os.path.exists(model_h5))

        sys.exit(998)

def latest_Y(company):
    filepath = os.path.join(model_dir(company), "y.pkl")

    y = None
    with open(filepath, "rb") as in_file:
        y = pickle.load(in_file)

    return y

def get_connected_components(g, dropped_threshold=10):
    results = [[]]
    width, height = len(g), len(g[0])

    def DFS(x, y):
        g[x, y] = 0

        for dx in range(-1, 2, 1):
            for dy in range(-1, 2, 1):
                pos_x, pos_y = x+dx, y+dy
                if pos_x > -1 and pos_y > -1 and pos_x < width and pos_y < height and g[pos_x, pos_y]:
                    DFS(pos_x, pos_y)

                    results[-1].append((pos_x, pos_y))

    for i in range(len(g)):
        for j in range(len(g[i])):
            if g[i, j]:
                DFS(i, j)

                if results[-1]:
                    if len(results[-1]) < dropped_threshold:
                        del results[-1]

                    results.append([])

    del results[-1]

    return results

def calculate_rect_gap(rects):
    gaps = []

    for idx in range(len(rects)-1):
        gap = rects[idx+1][0] - rects[idx][2]
        gaps.append(gap)

    return gaps

def downgrade_image(img, pix_filter):
    width, height = img.size

    g = []
    pixdata = img.load()
    for y in xrange(height):
        lines = []
        for x in xrange(width):
            if pixdata[x, y][0] < pix_filter or pixdata[x, y][1] < pix_filter or pixdata[x, y][2] < pix_filter:
                lines.append(1)
            else:
                lines.append(0)
        g.append(lines)

    return np.array(g)

def downgrade_image_l(img, pix_filter):
    width, height = img.size

    pixdata = img.load()
    for y in xrange(height):
        for x in xrange(width):
            if pixdata[x, y][0] < pix_filter or pixdata[x, y][1] < pix_filter or pixdata[x, y][2] < pix_filter:
                pixdata[x, y] = (0, 0, 0)
            else:
                pixdata[x, y] = (255, 255, 255)

def get_cropped_rects(rects, width, height, bold, threshold=(34, 96)):
    cropped_rects = []
    for poss in rects:
        top, left = min([x[0] for x in poss]), min([x[1] for x in poss])
        bottom, right = max([x[0] for x in poss]), max([x[1] for x in poss])

        left, top = max(0, left-bold), max(0, top-bold)
        right, bottom = min(width, right+bold), min(height, bottom+bold*2)

        #print bottom, height
        if right-left < threshold[0] and bottom != height:
            cropped_rects.append((left, top, right, bottom))

    return sorted(cropped_rects, key=lambda x: x[0])
