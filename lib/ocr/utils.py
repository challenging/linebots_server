#!/usr/bin/env python

import os
import numpy as np

from keras.models import model_from_json
from PIL import Image, ImageFilter, ImageEnhance

def data_dir():
    return os.path.join(os.path.dirname(__file__), "etc")

def model_dir():
    return os.path.join(data_dir(), "model")

def cracker_dir():
    return os.path.join(data_dir(), "cracker")

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

    print("Loaded model({}, {}) from disk".format(filepath_json, filepath_weight))

    return model

def latest_model(model):
    basepath_model_json = os.path.join(model_dir(), "model.json")
    basepath_model_h5 = os.path.join(model_dir(), "model.h5")

    return load(basepath_model_json, basepath_model_h5, model)

def check_folder(filepath, is_folder=False):
    folder = filepath
    if not is_folder:
        folder = os.path.dirname(filepath)

    if not os.path.exists(folder):
        os.makedirs(folder)

        print "create folder - {}".format(folder)
