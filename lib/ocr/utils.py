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

def get_connected_components(g, results, dropped_threshold=10):
    def DFS(x, y):
        g[x, y] = 0
        for dx in range(-1, 2, 1):
            for dy in range(-1, 2, 1):
                pos_x, pos_y = x+dx, y+dy
                if g[pos_x, pos_y]:
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
