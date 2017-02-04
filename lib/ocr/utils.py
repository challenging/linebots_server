#!/usr/bin/env python

import os
import sys
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

def latest_model(model):
    model_json = os.path.join(model_dir(), "model.json")
    model_h5 = os.path.join(model_dir(), "model.h5")

    if os.path.exists(model_json) and os.path.exists(model_h5):
        return load(model_json, model_h5, model)
    else:
        print "Not found {}({}), {}({})".format(\
            model_json, os.path.exists(model_json), model_h5, os.path.exists(model_h5))

        sys.exit(998)
