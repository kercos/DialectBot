import datetime
from datetime import datetime
from datetime import timedelta

def now(addMinutes=0):
    return datetime.now() + timedelta(minutes=int(addMinutes))

def get_today():
    return datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)

def delta_min(date1, date2):
    diff = date2 - date1
    min_sec = divmod(diff.days * 86400 + diff.seconds, 60) # (min,sec)
    return min_sec[0]

def ellapsed_min(date):
    return delta_min(date, now())

def get_last_week():
    return datetime.now() - timedelta(days=7)

def get_time_days_ago(deltaDay):
    return datetime.now() - timedelta(days=deltaDay)

def get_date_CET(date):
    if date is None: return None
    newdate = date + timedelta(hours=1)
    return newdate

def get_date_string(date):
    newdate = get_date_CET(date)
    time_day = str(newdate).split(" ")
    time = time_day[1].split(".")[0]
    day = time_day[0]
    return day + " " + time

def get_time_string(date):
    newdate = date + timedelta(hours=1)
    return str(newdate).split(" ")[1].split(".")[0]