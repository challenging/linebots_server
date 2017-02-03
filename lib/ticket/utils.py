#!/usr/bin/env python

import os

from lib.common.utils import check_folder, data_dir

def tra_dir(f):
    folder = os.path.join(data_dir("captcha"), "tra", f)
    check_folder(folder, is_folder=True)

    return folder

def tra_img_dir():
    return tra_dir("source")

def tra_screen_dir():
    return tra_dir("screenshot")

def tra_success_dir():
    return tra_dir("success")

def tra_ticket_dir():
    return tra_dir("ticket")
