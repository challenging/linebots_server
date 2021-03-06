#!/usr/bin/env python

import os
import sys
import time
import glob
import click
import pickle
import numpy as np

from sklearn.model_selection import train_test_split

from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Dropout
from keras.layers import Flatten
from keras.layers.convolutional import Convolution2D
from keras.layers.convolutional import MaxPooling2D
from keras.utils import np_utils
from keras import backend as K
K.set_image_dim_ordering('th')

from lib.common.utils import check_folder
from utils import save, data_dir, model_dir

# fix random seed for reproducibility
seed = 7
np.random.seed(seed)

def load_data(files, parts=range(0, 10)+["x"]):
    dataset_x, dataset_y = [], []

    for part in parts:
        for filepath in glob.iglob(files.format(part)):
            x = np.load(filepath)

            y = [0]*len(parts)
            y[parts.index(part)] = 1

            dataset_x.append(x)
            dataset_y.append(y)

    dataset_x = np.array(dataset_x)
    dataset_y = np.array(dataset_y)

    return dataset_x, dataset_y

mlp_preprocess = lambda dataset: dataset.reshape(dataset.shape[0], dataset.shape[1]*dataset.shape[2]).astype('float32') / 255
def mlp_model(input_dim, output_dim):
    model = Sequential()
    model.add(Dense(input_dim, input_dim=input_dim, init='normal', activation='relu'))
    model.add(Dense(output_dim, init='normal', activation='softmax'))

    # Compile model
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

    return model

def cnn_preprocess(dataset):
    h, w = dataset.shape[1], dataset.shape[2]
    dataset = dataset.reshape(dataset.shape[0], 1, h, w).astype('float32') / 255

    return dataset, h, w

def simple_cnn_model(shape, output_dim):
    # create model
    model = Sequential()
    model.add(Convolution2D(32, 5, 5, border_mode='valid', input_shape=shape, activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.2))
    model.add(Flatten())
    model.add(Dense(128, activation='relu'))
    model.add(Dense(output_dim, activation='softmax'))

    # Compile model
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

    return model

def thsr_complex_cnn_model(shape, output_dim):
    # create model
    model = Sequential()
    model.add(Convolution2D(48, 5, 5, border_mode='valid', input_shape=shape, activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Convolution2D(64, 4, 4, activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Convolution2D(128, 4, 4, activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.2))
    model.add(Flatten())
    model.add(Dense(128, activation='relu'))
    model.add(Dense(32, activation='relu'))
    model.add(Dense(output_dim, activation='softmax'))

    # Compile model
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

    return model

def tra_complex_cnn_model(shape, output_dim):
    # create model
    model = Sequential()
    model.add(Convolution2D(16, 5, 5, border_mode='valid', input_shape=shape, activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.2))
    model.add(Convolution2D(32, 4, 4, activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.2))
    model.add(Convolution2D(64, 4, 4, activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.2))
    model.add(Flatten())
    model.add(Dense(256, activation='relu'))
    model.add(Dropout(0.2))
    model.add(Dense(128, activation='relu'))
    model.add(Dropout(0.2))
    model.add(Dense(64, activation='relu'))
    model.add(Dense(output_dim, activation='softmax'))

    # Compile model
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

    return model

def fit(model, X_train, X_validation, y_train, y_validation, nepoch=32, batch_size=16):
    model.fit(X_train, y_train, validation_data=(X_validation, y_validation), nb_epoch=nepoch, batch_size=batch_size, verbose=1)

@click.command()
@click.option("-m", "--mode", type=click.Choice(["mlp", "simple_cnn", "complex_cnn"]))
@click.option("-c", "--company", type=click.Choice(["tra", "thsr"]))
@click.option("-t", "--test-size", default=0.33)
@click.option("-e", "--epoch", default=16)
@click.option("-b", "--batch-size", default=32)
def main(mode, company, test_size, epoch, batch_size):
    basepath_data_input = os.path.join(data_dir(), company, "train", "number")

    parts = range(0, 10) + ["x"]
    if company == "thsr":
        parts = []
        for folder in os.listdir(basepath_data_input):
            if len(folder) == 1:
                parts.append(folder)

    dataset_x, dataset_y = load_data(os.path.join(basepath_data_input, "{}", "*.npy"), parts)

    model = None
    if mode == "mlp":
        dataset_x = mlp_preprocess(dataset_x)

        model = mlp_model(dataset_x.shape[1], dataset_y.shape[1])
    elif mode.find("cnn") > -1:
        dataset_x, h, w = cnn_preprocess(dataset_x)
        print dataset_x.shape, h, w

        if mode == "simple_cnn":
            model = simple_cnn_model((1, h, w), dataset_y.shape[1])
        elif mode == "complex_cnn":
            if company == "tra":
                model = tra_complex_cnn_model((1, h, w), dataset_y.shape[1])
            elif company == "thsr":
                model = thsr_complex_cnn_model((1, h, w), dataset_y.shape[1])
        else:
            raise NotImplementedError

    X_train, X_validation, y_train, y_validation = train_test_split(dataset_x, dataset_y, test_size=test_size)

    fit(model, X_train, X_validation, y_train, y_validation, epoch, batch_size)
    scores = model.evaluate(X_validation, y_validation, verbose=0)
    print "Baseline Error of Validation Set: {:.8f}%".format(100-scores[1]*100)

    folder = os.path.join(model_dir(company), str(int(time.time())))
    check_folder(folder, is_folder=True)

    with open(os.path.join(folder, "y.pkl"), "wb") as out_file:
        pickle.dump(parts, out_file)

    filepath_json = os.path.join(folder, "model={}.epoch={}.batch={}.json".format(mode, epoch, batch_size))
    filepath_weight = os.path.join(folder, "model={}.epoch={}.batch={}.h5".format(mode, epoch, batch_size))
    save(filepath_json, filepath_weight, model)

if __name__ == "__main__":
    main()
