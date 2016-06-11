# -*- coding: utf-8 -*-

import urllib, urllib2
import logging
import json

import key
import re
import random


def getFile(file_id):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'getFile', urllib.urlencode({
            'file_id': file_id,
        })).read()
        logging.info('asked for file: ')
        logging.info(resp)
        file_path = json.loads(resp)['result']['file_path']
        logging.info('file path:' + file_path)
        file = urllib2.urlopen(key.BASE_URL_FILE + file_path).read()
        return file
    except urllib2.HTTPError, err:
        logging.info("exception:" + str(err))

def representsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def representsLong(s):
    try:
        long(s)
        return True
    except ValueError:
        return False

re_digits = re.compile('^\d+$')

def hasOnlyDigits(s):
    return re_digits.match(s) != None

def getRandomFloat(maxValue=1.0):
    return random.random() * maxValue