#!/usr/bin/env python

import re

def check_taiwan_id_number(id_number=None):
    if not id_number:
        return False #'no id number'

    if len(id_number) <> 10:
        return False #'length is not 10'

    if id_number[1:2] not in ['1', '2']:
        return False #'id number not 1 or 2'

    id_number = id_number.upper()

    tab = (
        ('A', (1, 0)),
        ('B', (1, 1)),
        ('C', (1, 2)),
        ('D', (1, 3)),
        ('E', (1, 4)),
        ('F', (1, 5)),
        ('G', (1, 6)),
        ('H', (1, 7)),
        ('J', (1, 8)),
        ('K', (1, 9)),
        ('L', (2, 0)),
        ('M', (2, 1)),
        ('N', (2, 2)),
        ('P', (2, 3)),
        ('Q', (2, 4)),
        ('R', (2, 5)),
        ('S', (2, 6)),
        ('T', (2, 7)),
        ('U', (2, 8)),
        ('V', (2, 9)),
        ('W', (3, 0)),
        ('X', (3, 1)),
        ('Y', (3, 2)),
        ('Z', (3, 3)),
        ('I', (3, 4)),
        ('O', (3, 5)),
    )

    regex = re.compile('^[A-Z]{1}[12]{1}[0-9]{8}')
    if not regex.match(id_number):
        return False #'id format not good'

    get_key = False
    ch = id_number[0:1]
    for key, val in tab:
        if ch == key:
            get_key = True
            break

    if not get_key:
        return False #'char not match'

    val1 = val[0]
    val2 = val[1]
    id_sum = val1 * 1 + val2 * 9
    id_sum += int(id_number[1:2]) * 8
    id_sum += int(id_number[2:3]) * 7
    id_sum += int(id_number[3:4]) * 6
    id_sum += int(id_number[4:5]) * 5
    id_sum += int(id_number[5:6]) * 4
    id_sum += int(id_number[6:7]) * 3
    id_sum += int(id_number[7:8]) * 2
    id_sum += int(id_number[8:9]) * 1
    mod_val = id_sum % 10
    if 0 == mod_val:
        check_num = 0
    else:
        check_num = 10 - mod_val

    if id_number[9:10] <> str(check_num):
        return False         # '%s | %s' % (id_number[9:10], check_num)

    return True
