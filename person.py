# -*- coding: utf-8 -*-

import logging
from google.appengine.ext import ndb
import recording
import key

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

    def setState(self, newstate, put=True):
        self.last_state = self.state
        self.state = newstate
        if put:
            self.put()

    def getName(self):
        return self.name.encode('utf-8')

    def getLastName(self):
        return self.last_name.encode('utf-8') if self.last_name!='-' else ''

    def getUsername(self):
        return self.username.encode('utf-8')

    def getNameLastName(self):
        result = self.getName() + ' ' + self.getLastName()
        return result.strip()

    def getNameLastNameUserName(self):
        result = self.getNameLastName()
        if self.username != '-':
            result += ' @' + self.getUsername()
        return result

    def setLast_recording_file_id(self, file_id, put=True):
        self.last_recording_file_id = file_id
        if put:
            self.put()

    def isAdmin(self):
        return self.chat_id in key.MASTER_CHAT_ID

def addPerson(chat_id, name):
    p = Person(
        id=str(chat_id),
        name=name,
        chat_id=chat_id,
    )
    p.put()
    return p

def updateUsername(p, username):
    if (p.username!=username):
        p.username = username
        p.put()

def setState(p, state):
    p.state = state
    p.put()

def setLocation(p, latitude, longitude):
    p.location =  ndb.GeoPt(latitude, longitude)
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

def getLastRecordingLatLonLocation(p):
    rec = recording.getRecordingCheckIfUrl(p.last_recording_file_id)
    return rec.location.lat, rec.location.lon

