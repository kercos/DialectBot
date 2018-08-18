# -*- coding: utf-8 -*-

import logging
from google.appengine.ext import ndb
import recording
import key
import utility

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

    def getFirstName(self, escapeMarkdown=True):
        if escapeMarkdown:
            return utility.escapeMarkdown(self.name.encode('utf-8'))
        return self.name.encode('utf-8')

    def getLastName(self, escapeMarkdown=True):
        if self.last_name==None:
            return None
        if escapeMarkdown:
            return utility.escapeMarkdown(self.last_name.encode('utf-8'))
        return self.last_name.encode('utf-8')

    def getUsername(self):
        return self.username.encode('utf-8') if self.username else None

    def getUserInfoString(self, escapeMarkdown=True):
        info = self.getFirstName(escapeMarkdown)
        if self.last_name:
            info += ' ' + self.getLastName(escapeMarkdown)
        if self.username:
            info += ' @' + self.getUsername()
        info += ' ({})'.format(self.chat_id)
        return info

    def setEnabled(self, enabled, put=False):
        self.enabled = enabled
        if put:
            self.put()

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

def getPeopleCount():
    cursor = None
    more = True
    total = 0
    while more:
        keys, cursor, more = Person.query().fetch_page(1000, start_cursor=cursor, keys_only=True)
        total += len(keys)
    return total
