# -*- coding: utf-8 -*-

from datetime import datetime as datetime
from pytz.gae import pytz

UTC_ZONE = pytz.timezone('UTC')
CET_ZONE = pytz.timezone('CET')

def nowCET():
    #return datetime.now()
    utc = datetime.now()
    utc = utc.replace(tzinfo=UTC_ZONE)
    return utc.astimezone(CET_ZONE)

def dateString(dt):
    return dt.strftime('%d/%m/%y')

def dateTimeString(dt=None):
    if dt == None:
        dt = nowCET()
    return dt.strftime('%d/%m/%y %H:%M:%S')

def get_datetime_ddmmyyyy(s):
    return datetime.strptime(s, '%d%m%Y')

def get_date_long_time_ago():
    return datetime.strptime('01011800', '%d%m%Y')
