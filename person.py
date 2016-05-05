# -*- coding: utf-8 -*-

import logging
from google.appengine.ext import ndb
import recording

class Person(ndb.Model):
    chat_id = ndb.IntegerProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty(default='-')
    username = ndb.StringProperty(default='-')
    state = ndb.IntegerProperty(default=-1, indexed=True)
    last_mod = ndb.DateTimeProperty(auto_now=True)
    location = ndb.GeoPtProperty()
    last_recording_file_id = ndb.StringProperty()
    enabled = ndb.BooleanProperty(default=True)


def addPerson(chat_id, name):
    p = Person.get_or_insert(str(chat_id))
    p.name = name
    p.chat_id = chat_id
    p.put()
    return p

def updateUsername(p, username):
    if (p.username!=username):
        p.username = username
        p.put()

def setState(p, state):
    p.state = state
    p.put()

def setLocation(p, loc):
    p.location =  ndb.GeoPt(loc['latitude'], loc['longitude'])
    p.put()

def getPersonByChatId(chat_id):
    return Person.get_by_id(str(chat_id))

def removeLastRecording(p):
    recording.deleteRecording(p.last_recording_file_id)
    p.last_recording_file_id =  None
    p.put()

def setLastRecording(p, recording):
    if recording.file_id:
        p.last_recording_file_id =  recording.file_id
    else:
        p.last_recording_file_id =  recording.url
    p.put()

def getLastRecordingLocation(p):
    rec = recording.getRecordingCheckIfUrl(p.last_recording_file_id)
    lat = rec.location.lat
    lon = rec.location.lon
    loc = {'latitude': lat, 'longitude': lon}
    return loc

