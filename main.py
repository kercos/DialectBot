# -*- coding: utf-8 -*-

#import json'libs'
import json
import logging
import urllib
import urllib2
import person
from person import Person
from datetime import datetime
from datetime import timedelta
from time import sleep
# import requests
import multipart
import recording
from recording import Recording
import geoUtils

# for sending images
from PIL import Image
import multipart
import random
import StringIO
import requests

import key
import emoij
import time_util

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.api import channel
from google.appengine.api import taskqueue
from google.appengine.ext import deferred
from google.appengine.ext.db import datastore_errors

#from google.appengine.ext import vendor
#vendor.add('lib')

import webapp2
import copy
import itertools
import math
import operator
#from flask import Flask, jsonify

import gettext
import utility

from jinja2 import Environment, FileSystemLoader

# ================================
WORK_IN_PROGRESS = False
# ================================


# ================================
# ================================
# ================================

DASHBOARD_DIR_ENV = Environment(loader=FileSystemLoader('dashboard'), autoescape = True)

ISTRUZIONI =  \
"""
Sono @DialectBot, uno *strumento gratuito e aperto alla comunità* per condividere registrazioni nei diversi dialetti. \
Hai la possibilità di 👂 ascoltare gli audio che sono già stati inseriti o 🗣 registrarne di nuovi.

Se pensi di non parlare nessun dialetto specifico ti consigliamo \
di utilizzare questo strumento per registrare parenti, amici o persone \
che incontri quando ti capita di viaggiare tra paesini sperduti in Italia.

Se vai sul sito http://dialectbot.appspot.com potrai *visualizzare* (e *ascoltare*) tutte le \
registrazioni sulla *mappa* 🗺 !

Aiutaci a far conoscere questo bot invitando altri amici e votandolo su \
[telegramitalia](telegramitalia.it/dialectbot) e su [storebot](telegram.me/storebot?start=dialectbot)

Per maggiori informazioni contatta @kercos

Buon 👂 ascolto e buona 🗣 registrazione a tutti!

"""

PLACE_INSTRUCTIONS = \
"""
Il luogo della registrazione è impostato su: {0} \
(se il luogo non è corretto premi su 🔀🌍 *CAMBIA LUOGO*).
"""

MIC_INSTRUCTIONS = \
"""
⭐ COME REGISTRARE ⭐
Quando sei pronta/o *tieni premuto il tasto del microfono* 🎙 (in basso) e \
*pronuncia* 🗣 una frase nel dialetto del luogo inserito, ad esempio un proverbio o un modo di dire.
"""

ISTRUZIONI_POSIZIONE = \
"""
Hai tre modi per inserire il luogo del dialetto che vuoi registrare:
📍 *Premi* su INVIA POSIZIONE se vuoi inviare la tua posizione corrente, oppure...
🖊 *Scrivi* qua sotto il *nome del luogo* di cui vuoi inserire una registrazione (ad esempio Roma), oppure...
🌍 *Seleziona una posizione nella mappa* seguendo le seguenti istruzioni:
      🔹 premi la graffetta (📎 ) in basso e premi su "Posizione"
      🔹 seleziona e invia una posizione dalla mappa.

"""

ISTRUZIONI_POSIZIONE_GUESS = \
"""
Hai due modi per indovinare il luogo della registrazione:
🖊 *Scrivi* qua sotto il *nome del luogo* (ad esempio 'Palermo'), oppure...
🌍 *Seleziona una posizione nella mappa* seguendo le seguenti istruzioni:
      📎 premi la graffetta in basso e premi su "Posizione"
      📍 seleziona e invia una posizione dalla mappa.
"""

ISTRUZIONI_POSIZIONE_SEARCH = \
"""
Hai due modi per cercare le registrazioni vicino ad un determinato luogo:
🖊 *Scrivi* qua sotto il *nome del luogo* (ad esempio 'Palermo'), oppure...
🌍 *Seleziona una posizione nella mappa* seguendo le seguenti istruzioni:
      📎 premi la graffetta in basso e premi su "Posizione"
      📍 seleziona e invia una posizione dalla mappa.
"""

MESSAGE_FOR_FRIENDS = \
"""
Ciao, ho scoperto @dialectbot, un tool gratuito e aperto alla comunità \
per ascoltare e registrare i dialetti italiani. \
Provalo premendo su @dialectbot!
"""

STATES = {
    -2: 'Setting posizione',
    -1: 'Initial with ASCOLTA, REGISTRA e HELP',
     0:   'Started',
    20: 'Registra',
    21: 'Confirm recording',
    22: 'Ask for transcription',
    30: 'Ascolta',
    31: 'Indovina Luogo',
    32: 'Ricerca Luogo',
    8:  'Info',
    9:  'Admin',
    91: 'Amin -> approva registrazioni'
}

MIC = u'\U0001F399'.encode('utf-8')
EAR = u'\U0001F442'.encode('utf-8')
INFO = u'\U00002139'.encode('utf-8')
SPEAKING_HEAD = u'\U0001F5E3'.encode('utf-8')
CANCEL = u'\U0000274C'.encode('utf-8')
SEARCH = u'\U0001F50E'.encode('utf-8')
POINT_LEFT = u'\U0001F448'.encode('utf-8')
WORLD = u'\U0001F30D'.encode('utf-8')
CLOCK = u'\U000023F2'.encode('utf-8')
CALENDAR = u'\U0001F4C5'.encode('utf-8')
FROWNING_FACE = u'\U0001F641'.encode('utf-8')
HUNDRED = u'\U0001F4AF'.encode('utf-8')
CLAPPING_HANDS = b'\xF0\x9F\x91\x8F'
SMILY = u'\U0001F60A'.encode('utf-8')
UNDER_CONSTRUCTION = u'\U0001F6A7'.encode('utf-8')

BOTTONE_ANNULLA = CANCEL + " Annulla"
BOTTONE_INDIETRO = emoij.LEFTWARDS_BLACK_ARROW + ' ' + "Indietro"
BOTTONE_REGISTRA = SPEAKING_HEAD + " REGISTRA"
BOTTONE_ASCOLTA = EAR + " ASCOLTA"
BOTTONE_INVITA = "📩 INVITA UN AMICO"
BOTTONE_INFO = INFO + " INFO"
BOTTONE_ADMIN = "🛠 ADMIN"
BOTTONE_INDOVINA_LUOGO = WORLD + POINT_LEFT + " INDOVINA LUOGO"
BOTTONE_CERCA_LUOGO = SEARCH + " CERCA LUOGO"
BOTTONE_RECENTI = CALENDAR + " REGISTRAZIONI RECENTI"
BOTTONE_TUTTE = HUNDRED + " TUTTE LE REGISTRAZIONI"
BOTTONE_CAMBIA_LUOGO = "🔀🌍 CAMBIA LUOGO"

BOTTONE_CONTACT = {
    'text': "Invia il tuo contatto",
    'request_contact': True,
}

BOTTONE_INVIA_LOCATION = {
    'text': "📍 INVIA POSIZIONE",
    'request_location': True,
}

BOTTONE_CALLBACK1 = {
    'text': "button 1",
    'callback_data': "sample data 1",
}

BOTTONE_CALLBACK2 = {
    'text': "button 2",
    'callback_data': "sample data 2",
}

BOTTONE_CALLBACK3 = {
    'text': "button 2",
    'callback_data': "sample data 3",
}


# ================================
# ================================
# ================================

def restart(p, txt=None):
    reply_txt = (txt + '\n\n') if txt!=None else ''
    reply_txt += "Premi su *{0}* o *{1}* se vuoi ascoltare o registrare una frase in un dialetto.".format(
        BOTTONE_ASCOLTA, BOTTONE_REGISTRA
    )
    second_row_buttons = [BOTTONE_INFO]
    if p.isAdmin():
        second_row_buttons.append(BOTTONE_ADMIN)
    tell(p.chat_id, reply_txt, kb=[[BOTTONE_ASCOLTA,BOTTONE_REGISTRA], second_row_buttons])
    person.setState(p, -1)

def restartAllUsers(msg):
    qry = Person.query()
    count = 0
    for p in qry:
        if (p.enabled): # or p.state>-1
            restart(p)
            tell(p.chat_id, msg)
            sleep(0.100) # no more than 10 messages per second
    logging.debug("Succeffully restarted users: " + str(count))
    return count

def restartTest(msg):
    qry = Person.query(Person.chat_id==key.PINCO_PALLINO_CHAT_ID)
    count = 0
    for p in qry:
        if (p.enabled): # or p.state>-1
            tell(p.chat_id, msg)
            restart(p)
            sleep(0.100) # no more than 10 messages per second
    logging.debug("Succeffully restarted users: " + str(count))
    return count


def init_user(p, name, last_name, username):
    if (p.name.encode('utf-8') != name):
        p.name = name
        p.put()
    if (p.getLastName() != last_name):
        p.last_name = last_name
        p.put()
    if (p.username != username):
        p.username = username
        p.put()
    if not p.enabled:
        p.enabled = True
        p.put()

def get_date_CET(date):
    if date is None: return None
    newdate = date + timedelta(hours=1)
    return newdate

def get_time_string(date):
    newdate = date + timedelta(hours=1)
    return str(newdate).split(" ")[1].split(".")[0]

def broadcast(sender_chat_id, msg, restart_user=False, curs=None, enabledCount = 0):
    #return

    BROADCAST_COUNT_REPORT = utility.unindent(
        """
        Mesage sent to {} people
        Enabled: {}
        Disabled: {}
        """
    )

    try:
        users, next_curs, more = Person.query().fetch_page(50, start_cursor=curs)
    except datastore_errors.Timeout:
        sleep(1)
        deferred.defer(broadcast, sender_chat_id, msg, restart_user, curs, enabledCount)
        return

    for p in users:
        if p.enabled:
            enabledCount += 1
            if restart_user:
                restart(p)
            tell(p.chat_id, msg, sleepDelay=True)

    if more:
        deferred.defer(broadcast, sender_chat_id, msg, restart_user, next_curs, enabledCount)
    else:
        total = Person.query().count()
        disabled = total - enabledCount
        msg_debug = BROADCAST_COUNT_REPORT.format(str(total), str(enabledCount), str(disabled))
        tell(sender_chat_id, msg_debug)

def getRecentRecordings(p):
    recordings = ''
    qry = Recording.query(Recording.approved == recording.REC_APPROVED_STATE_TRUE).order(-Recording.date_time).fetch(8)
    for r in qry:
        name = person.getPersonByChatId(r.chat_id).name.encode('utf-8')
        recordings += '/rec_' + str(r.key.id()) + ' - ' + name + ' - ' + str(r.date_time.date()) + '\n'
    tell(p.chat_id,
         "ULTIME REGISTRAZIONI:\n\n" + recordings +
         "\nPremi su uno dei link sopra per ascoltare la registrazione corrispondente.",
         kb=[[BOTTONE_INDIETRO]], markdown=False)

def getAllRecordings(p):
    recordings = ''
    qry = Recording.query(Recording.chat_id > 0)
    for r in qry:
        name = person.getPersonByChatId(r.chat_id).name
        recordings += '/rec_' + str(r.key.id()) + ' - ' + name + ' - ' + str(r.date_time.date()) + '\n'
    tell(p.chat_id,
         "ULTIME REGISTRAZIONI:\n\n" + recordings +
         "\nPremi su uno dei link sopra per ascoltare la registrazione corrispondente.",
         kb=[[BOTTONE_INDIETRO]])

def getLastContibutors(daysAgo):
    dateThreshold = time_util.get_time_days_ago(daysAgo)
    names = set()
    recsCommands = []
    count = 0
    recs = Recording.query(Recording.date_time > dateThreshold, Recording.approved == recording.REC_APPROVED_STATE_TRUE).fetch()
    for r in recs:
        if r.chat_id<=0:
            continue
        name = person.getPersonByChatId(r.chat_id).name
        names.add(name)
        recsCommands.append(r.getRecCommand())
        count += 1
    namesString = ', '.join([x.encode('utf-8') for x in names])
    recCommandsString = '\n'.join(['🎙 {}'.format(x) for x in recsCommands])
    return count, namesString, recCommandsString

def sendNewRecordingNotice(p):
    rec = recording.getRecording(p.last_recording_file_id)
    logging.debug("Sending new recording notice /rec_" + str(rec.key.id()))
    tell(key.FEDE_CHAT_ID, "New recording: /rec_" + str(rec.key.id()) + " from user {0}: {1}".format(
        str(p.chat_id), p.getUserInfoString()), markdown=False)

def getInfoCount():
    c = Person.query().count()
    #msg = "Siamo ora " + str(c) + " persone iscritte a DialectBot! " \
    #      "Vogliamo crescere assieme! Invita altre persone ad unirsi!"
    return c

def tellmyself(p, msg):
    tell(p.chat_id, "Udiete udite... " + msg)

def tell_masters(msg, markdown=False, one_time_keyboard=False):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg, markdown=markdown, one_time_keyboard = one_time_keyboard, sleepDelay=True)

def tell_fede(msg):
    for i in range(100):
        tell(key.FEDE_CHAT_ID, "prova " + str(i))
        sleep(0.1)

def tell_person(chat_id, msg, markdown=False):
    tell(chat_id, msg, markdown=markdown)
    p = ndb.Key(Person, str(chat_id)).get()
    if p and p.enabled:
        return True
    return False


def tell(chat_id, msg, kb=None, markdown=True, inlineKeyboardMarkup=False,
         one_time_keyboard=True, sleepDelay=False):
    replyMarkup = {
        'resize_keyboard': True,
        'one_time_keyboard': one_time_keyboard
    }
    if kb:
        if inlineKeyboardMarkup:
            replyMarkup['inline_keyboard'] = kb
        else:
            replyMarkup['keyboard'] = kb
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendMessage', urllib.urlencode({
            'chat_id': chat_id,
            'text': msg,  # .encode('utf-8'),
            'disable_web_page_preview': 'true',
            'parse_mode': 'Markdown' if markdown else '',
            # 'reply_to_message_id': str(message_id),
            'reply_markup': json.dumps(replyMarkup),
        })).read()
        logging.info('send response: ')
        logging.info(resp)
        resp_json = json.loads(resp)
        return resp_json['result']['message_id']
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = person.getPersonByChatId(chat_id)
            p.setEnabled(False, put=True)
            # logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))
        else:
            logging.debug('Raising unknown err in tell() with msg = ' + msg)
            raise err
    if sleepDelay:
        sleep(0.1)

def sendVoiceFile(chat_id):
    try:
        #img = urllib2.urlopen('https://dl.dropboxusercontent.com/u/12016006/tmp/image.jpg').read()
        #voice = urllib2.urlopen('https://dl.dropboxusercontent.com/u/12016006/tmp/squagliare.ogg').read()
        voice = urllib2.urlopen('https://dl.dropboxusercontent.com/u/12016006/tmp/acqua.ogg').read()
        resp = multipart.post_multipart(
                key.BASE_URL + 'sendVoice',
                [('chat_id', str(chat_id)),],
                [('voice', 'voice.ogg', voice),]
        )
        logging.info('send response: ')
        logging.info(resp)
        respParsed = json.loads(resp)
        logging.debug('file id: ' + str(respParsed['result']['voice']['file_id']))
        #logging.debug('keys: ' + resp.keys())
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id==chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.name.encode('utf-8') + _(' ') + str(chat_id))

def sendLocation(chat_id, latitude, longitude):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendLocation', urllib.urlencode({
            'chat_id': chat_id,
            'latitude': latitude,
            'longitude': longitude,
            #'reply_markup': json.dumps({
                #'one_time_keyboard': True,
                #'resize_keyboard': True,
                #'keyboard': kb,  # [['Test1','Test2'],['Test3','Test8']]
                #'reply_markup': json.dumps({'hide_keyboard': True})
            #}),
        })).read()
        logging.info('send location: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id==chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.name.encode('utf-8') + _(' ') + str(chat_id))

def sendTranslation(chat_id, rec):
    translation = rec.translation
    if translation:
        tell(chat_id, "Spiegazione: " + translation.encode('utf-8'))
    else:
        tell(chat_id, "Nessuna traduzione.")

def sendVoiceFileId(chat_id, file_id):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendVoice', urllib.urlencode({
            'chat_id': str(chat_id),
            'voice': str(file_id), #.encode('utf-8'),
        })).read()
        logging.info('send voice: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id==chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))
        else:
            logging.info('Error occured: ' + str(err))

def sendAudio(chat_id, file_id):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendAudio', urllib.urlencode({
            'chat_id': str(chat_id),
            'audio': str(file_id), #.encode('utf-8'),
            'performer': "From Vivaio Acustico delle Lingue e dei Dialetti d'Italia",
            'title': "From Vivaio Acustico delle Lingue e dei Dialetti d'Italia"
        })).read()
        logging.info('send audio: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id==chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))
        else:
            logging.info('Error occured: ' + str(err))

def sendVoiceLocationTranslationFromCommand(p, rec_command, userInfo = False):
    digits = rec_command[5:]
    if utility.hasOnlyDigits(digits):
        rec_id = long(digits)
        rec = Recording.get_by_id(rec_id)
        if rec is None:
            tell(p.chat_id, 'No recording found!')
        else:
            sendVoiceLocationTranslation(p, rec, userInfo=userInfo)
    else:
        tell(p.chat_id, FROWNING_FACE + "Input non valido.")

def sendVoiceLocationTranslation(p, rec, userInfo = False):
    if userInfo:
        user = person.getPersonByChatId(rec.chat_id)
        tell(p.chat_id, 'Registrazione eseguita da: {}'.format(user.getFirstName()))
    tell(p.chat_id, 'Audio:')
    sendVoiceFileId(p.chat_id, rec.file_id)
    msg = 'Luogo: ' + geoUtils.getComuneProvinciaFromCoordinates(rec.location.lat, rec.location.lon)
    tell(p.chat_id, msg)
    sendLocation(p.chat_id, rec.location.lat, rec.location.lon)
    sendTranslation(p.chat_id, rec)

def format_distance(dst):
    if (dst>=10):
        return str(round(dst, 0)) + " Km"
    if (dst>=1):
        return str(round(dst, 1)) + " Km"
    return str(int(dst*1000)) + " m"

def format_and_comment_distance(dst):
    fmt_dst = format_distance(dst)
    if (dst>=500):
        return fmt_dst + ". Sei molto lontano! 😜"
    if (dst>=250):
        return fmt_dst + ". Puoi fare di meglio! 😉"
    if (dst>=100):
        return fmt_dst + ". Non male! 🤔"
    if (dst>=50):
        return fmt_dst + ". Brava/o ci sei andata/o molto vicino! 😄"
    if (dst>=15):
        return fmt_dst + ". Bravissima/o! 👍😄"
    return fmt_dst + ". Wow, Strepitoso! 🎉🎉👍😄🎉🎉"


# ================================
# SEND ACTION
# ================================

def sendWaitingAction(chat_id, action_type='typing'):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendChatAction', urllib.urlencode({
            'chat_id': chat_id,
            'action': action_type,
        })).read()
        logging.info('send venue: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id == chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.getUserInfoString())
        else:
            logging.info('Unknown exception: ' + str(err))


# ================================
# ================================
# ================================

def sendVoiceUrl(chat_id, url):
    try:
        voice = urllib2.urlopen(url).read()
        resp = multipart.post_multipart(
                key.BASE_URL + 'sendVoice',
                [('chat_id', str(chat_id)),],
                [('voice', 'voice.ogg', voice),]
        )
        logging.info('send response: ')
        logging.info(resp)
        #respParsed = json.loads(resp)
        #logging.debug('file id: ' + str(respParsed['result']['voice']['file_id']))
        #file_id = respParsed['result']['voice']['file_id']
        #rec.url = None
        #rec.file_id = file_id
        #rec.put()
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id==chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.name.encode('utf-8') + _(' ') + str(chat_id))

# ================================
# ================================
# ================================

def sendRecording(chat_id, rec):
    if rec.file_id:
        sendVoiceFileId(chat_id, rec.file_id)
    else:
        logging.debug("Setting last recording via url: " + rec.url)
        sendVoiceUrl(chat_id, rec.url)

def dealWithRandomRecording(p):
    randomRecording = recording.getRandomRecording()
    if not randomRecording:
        tell(p.chat_id, "Scusa, non abbiamo altre registrazioni disponibili, chidi ai tuoi amici di inserirne altre", kb=[[BOTTONE_ANNULLA]])
        restart(p)
    else:
        tell(p.chat_id, "Ascolta l'audio seguente e prova ad indovinare da dove proviene 😀")
        sendRecording(p.chat_id, randomRecording)
        person.setLastRecording(p,randomRecording)
        logging.debug("Last recording id: " + str(p.last_recording_file_id))
        tell(p.chat_id, ISTRUZIONI_POSIZIONE_GUESS, kb=[["ASCOLTA NUOVA REGISTRAZIONE"],[BOTTONE_INDIETRO]])
        person.setState(p, 31)

def dealWithGuessedLocation(p,guessed_loc):
    lat_guessed = guessed_loc['latitude']
    lon_guessed = guessed_loc['longitude']
    lat_gold, lon_gold  = person.getLastRecordingLatLonLocation(p)
    logging.debug('Gold loc: ' + str((lat_gold, lon_gold)))
    logging.debug('Guessed loc: ' + str(guessed_loc))
    luogo = '*' + geoUtils.getComuneProvinciaFromCoordinates(lat_gold, lon_gold) + '*'
    #dist = geoUtils.HaversineDistance(lat_guessed, lon_guessed, lat_gold, lon_gold)
    dist = geoUtils.distance((lat_guessed, lon_guessed), (lat_gold, lon_gold))
    distFormatted = format_and_comment_distance(dist)
    tell(p.chat_id, "Distanza: " + distFormatted + "\n" + "Questo il luogo preciso: " + luogo)
    rec = recording.getRecordingCheckIfUrl(p.last_recording_file_id)
    sendLocation(p.chat_id, lat_gold, lon_gold)
    sendTranslation(p.chat_id, rec)

def dealWithPlaceAndMicInstructions(p):
    lat, lon = p.location.lat, p.location.lon
    luogo = '*' + geoUtils.getComuneProvinciaFromCoordinates(lat, lon) + '*'
    if luogo==None:
        tell(p.chat_id, "Il luogo inserito non è stato riconosciuto, riprova.")
        tell(key.FEDE_CHAT_ID, "A user inserted a unrecognized location: {},{}".format(lat, lon))
        sendLocation(key.FEDE_CHAT_ID, lat, lon)
    instructions = PLACE_INSTRUCTIONS.format(luogo) + MIC_INSTRUCTIONS
    tell(p.chat_id, instructions, kb=[[BOTTONE_CAMBIA_LUOGO],[BOTTONE_INDIETRO]])
    person.setState(p, 20)

def dealWithFindClosestRecording(p, location):
    lat = location['latitude']
    lon = location['longitude']

    SEARCH_RADIUS_RANDOM_RADIUS = [(10,5),(25,10),(50,20)]

    rec = None
    for r1, r2 in SEARCH_RADIUS_RANDOM_RADIUS:
        rec = recording.getClosestRecording(lat, lon, r1, r2)
        if rec is not None:
            break

    if rec:
        logging.debug('Found recording id={} for location=({},{})'.format(rec.key.id(), lat, lon))
        tell(p.chat_id, "Trovata la seguente registrazione: ")
        sendRecording(p.chat_id, rec)
        sendLocation(p.chat_id, rec.location.lat, rec.location.lon)
        sendTranslation(p.chat_id, rec)
        luogo = '*' + geoUtils.getComuneProvinciaFromCoordinates(rec.location.lat, rec.location.lon) + '*'
        dst = geoUtils.distance((location['latitude'], location['longitude']),(rec.location.lat,rec.location.lon))
        tell(p.chat_id, "Luogo della registrazione: " + luogo +
             ". La distanza dal luogo inserito è di: " + format_distance(dst) + ".")
        tell(p.chat_id, "Se vuoi cercare un'altra registrazione inserisci una nuova località altrimenti premi 'Indietro'.")
    else:
        tell(p.chat_id, "Non ho trovato nessuna registrazione nelle vicinanze della posizione inserita. Riprova.\n" +
              ISTRUZIONI_POSIZIONE_SEARCH, kb = [[BOTTONE_INDIETRO]])
# ================================
# ================================
# ================================

ASCOLTA_MSG = \
"""
Premi su:
🌍👈 *INDOVINA LUOGO* se vuoi ascoltare una registrazione qualsiasi e indovinare da dove proviene
🔎 *CERCA LUOGO* se vuoi cercare una registrazione di un determinato luogo
📅 *REGISTRAZIONI RECENTI* per ascoltare le registrazioni più recenti
"""
#- TUTTE LE REGISTRAZIONI per ascoltare tutte le registrazioni

def goToAscolta(p):
    tell(p.chat_id, ASCOLTA_MSG,
         kb=[[BOTTONE_INDOVINA_LUOGO, BOTTONE_CERCA_LUOGO], [BOTTONE_RECENTI], [BOTTONE_INDIETRO]])
    person.setState(p, 30)

#BOTTONE_TUTTE

# ================================
# HANDLERS
# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(key.BASE_URL + 'getMe'))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        allowed_updates = ["message","inline_query", "chosen_inline_result", "callback_query"]
        data = {
            'url': key.WEBHOOK_URL,
            'allowed_updates': json.dumps(allowed_updates),
        }
        resp = requests.post(key.BASE_URL + 'setWebhook', data)
        logging.info('SetWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

class GetWebhookInfo(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'getWebhookInfo')
        logging.info('GetWebhookInfo Response: {}'.format(resp.text))
        self.response.write(resp.text)

class DeleteWebhook(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'deleteWebhook')
        logging.info('DeleteWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

class RedirectMappa(webapp2.RequestHandler):
    def get(self):
        self.redirect("http://dialectbot.appspot.com/audiomap/mappa.html")

class InfoAllUsersWeeklyHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        msg = getWeeklyMessage()
        broadcast(key.FEDE_CHAT_ID, msg, restart_user=True)

def getWeeklyMessage():
    people_count = getInfoCount()
    contr_count, contr_namesString, recCommandsString = getLastContibutors(7)
    msg = "Siamo ora " + str(people_count) + " persone iscritte a DialectBot!\n"
    if contr_count > 0:
        if contr_count == 1:
            msg += utility.unindent(
                """
                Nell'ultima settimana abbiamo ricevuto una registrazione!
                Un grande ringraziamento a *{}*! {}\n
                Se vuoi ascoltarla premi su questo comando:\n{}
                """.format(contr_namesString, CLAPPING_HANDS, recCommandsString)
            )
        else:
            msg += utility.unindent(
                """
                Nell'ultima settimana abbiamo ricevuto {} registrazioni!
                Un grande ringraziamento a *{}*! {}\n
                Se vuoi ascoltarle premi su questi comandi:\n{}
                """.format(contr_count, contr_namesString, CLAPPING_HANDS*contr_count, recCommandsString)
            )
    else:
        msg += "Purtroppo questa settimana non abbiamo ricevuto nessuna nuova registrazione " + FROWNING_FACE

    msg += "\nSe vai sul sito http://dialectbot.appspot.com potrai " \
           "*visualizzare* (e *ascoltare*) tutte le registrazioni sulla *mappa* 🗺 !"

    msg += "\n\n*Aiutaci a crescere*: aggiungi nuove registrazioni del tuo dialetto tramite il bot " \
           "e invita altre persone ad unirsi! " + SMILY
    return msg

# ================================
# ================================
# ================================

# ================================
# SWITCH TO STATE
# ================================
def redirectToState(p, new_state, **kwargs):
    if p.state != new_state:
        logging.debug("In redirectToState. current_state:{0}, new_state: {1}".format(str(p.state),str(new_state)))
        p.setState(new_state)
    repeatState(p, **kwargs)

# ================================
# REPEAT STATE
# ================================
def repeatState(p, **kwargs):
    methodName = "goToState" + str(p.state)
    method = possibles.get(methodName)
    if not method:
        tell(p.chat_id, "Si è verificato un problema (" + methodName +
              "). Segnalamelo mandando una messaggio a @kercos" + '\n' +
              "Ora verrai reindirizzato/a nella schermata iniziale.")
        restart(p)
    else:
        method(p, **kwargs)

# ================================
# state 8: Info
# ================================

def goToState8(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        kb = [
            [BOTTONE_INVITA],
            [BOTTONE_INDIETRO]
        ]

        tell(p.chat_id, ISTRUZIONI, kb)
    else:
        if input == '':
            tell(p.chat_id, "Input non valido.")
        elif input == BOTTONE_INVITA:
            tell(p.chat_id, "Inoltra il seguente messaggio a parenti e amici 😊")
            sendWaitingAction(p.chat_id)
            sleep(3)
            tell(p.chat_id, MESSAGE_FOR_FRIENDS, kb = [[BOTTONE_INDIETRO]])
        elif input == BOTTONE_INDIETRO:
            restart(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Scusa, non capisco quello che hai detto.")


# ================================
# state 9: Admin
# ================================

BOTTONE_APPROVA_REGISTRAZIONI = '✅❌ APPROVA REGISTRAZIONI'

def goToState9(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        reply_txt = 'Maschera principale amministratore'
        kb = [
            [BOTTONE_APPROVA_REGISTRAZIONI],
            [BOTTONE_INDIETRO]
        ]

        tell(p.chat_id, reply_txt, kb)
    else:
        if input == '':
            tell(p.chat_id, "Input non valido.")
        elif input == BOTTONE_APPROVA_REGISTRAZIONI:
            redirectToState(p, 91)
        elif input == BOTTONE_INDIETRO:
            restart(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Scusa, non capisco quello che hai detto.")

# ================================
# state 91: Admin - Approvazione Registrazioni
# ================================

BOTTONE_APPROVA = "👍 APPROVA"
BOTTONE_DISAPPROVA = "👎 DISAPPROVA"

USER_MSG = \
"""
La tua registrazione{0}è stata approvata.
Per riascoltarla premi su: /rec_{1}
Per maggiori infomazioni contattatta @kercos
"""

def goToState91(p, **kwargs):
    input = kwargs['input'] if 'input' in kwargs.keys() else None
    giveInstruction = input is None
    if giveInstruction:
        rec = Recording.query(Recording.approved == recording.REC_APPROVED_STATE_IN_PROGRESS).get()
        if rec:
            p.setLast_recording_file_id(rec.file_id)
            sendVoiceLocationTranslation(p, rec, userInfo=True)
            kb = [
                [BOTTONE_APPROVA, BOTTONE_DISAPPROVA],
                [BOTTONE_INDIETRO]
            ]
            tell(p.chat_id, "Approvi questa registrazione?", kb)
        else:
            kb = [[BOTTONE_INDIETRO]]
            tell(p.chat_id, "Non c'è nessuna registrazione da approvare", kb)
    else:
        if input == '':
            tell(p.chat_id, "Input non valido.")
        elif input == BOTTONE_APPROVA:
            rec = recording.getRecording(p.last_recording_file_id)
            tell(rec.chat_id, USER_MSG.format('', str(rec.key.id())), markdown=False)
            tell(p.chat_id, "Registrazione approvata!")
            rec.approve(recording.REC_APPROVED_STATE_TRUE)
            recording.appendRecordingInGeoJsonStructure(rec)
            sleep(2)
            repeatState(p)
        elif input == BOTTONE_DISAPPROVA:
            rec = recording.getRecording(p.last_recording_file_id)
            tell(rec.chat_id, USER_MSG.format(' NON ', str(rec.key.id())), markdown=False)
            tell(p.chat_id, "Registrazione NON approvata! "
                            "Se vuoi mandare maggiori info scrivi /sendText {0} text".format(str(rec.chat_id)))
            rec.approve(recording.REC_APPROVED_STATE_FALSE)
            sleep(2)
            repeatState(p)
        elif input == BOTTONE_INDIETRO:
            redirectToState(p, 9)
        else:
            tell(p.chat_id, FROWNING_FACE + " Scusa, non capisco quello che hai detto.")


# ================================
# ================================
# ================================

def dealWithsendTextCommand(p, sendTextCommand, markdown=False):
    split = sendTextCommand.split()
    if len(split)<3:
        tell(p.chat_id, 'Commands should have at least 2 spaces')
        return
    if not split[1].isdigit():
        tell(p.chat_id, 'Second argumnet should be a valid chat_id')
        return
    id = int(split[1])
    sendTextCommand = ' '.join(split[2:])
    if tell_person(id, sendTextCommand, markdown=markdown):
        user = person.getPersonByChatId(id)
        tell(p.chat_id, 'Successfully sent text to ' + user.name)
    else:
        tell(p.chat_id, 'Problems in sending text')


# ================================
# ================================
# ================================


class WebhookHandler(webapp2.RequestHandler):

    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        # update_id = body['update_id']
        if 'message' not in body:
            return
        message = body['message']
        #message_id = message.get('message_id')
        # date = message.get('date')
        if "chat" not in message:
            return
        # fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']
        if "first_name" not in chat:
            return
        text = message.get('text').encode('utf-8') if "text" in message else ""
        name = chat["first_name"].encode('utf-8')
        last_name = chat["last_name"].encode('utf-8') if "last_name" in chat else "-"
        username = chat["username"] if "username" in chat else "-"
        location = message["location"] if "location" in message else None
        voice = message["voice"] if "voice" in message else None
        audio = message["audio"] if "audio" in message else None
        document = message["document"] if "document" in message else None
        #logging.debug('location: ' + str(location))

        def reply(msg=None, kb=None, markdown=True, inlineKeyboardMarkup=False):
            tell(chat_id, msg, kb=kb, markdown=markdown, inlineKeyboardMarkup=inlineKeyboardMarkup)

        p = ndb.Key(Person, str(chat_id)).get()

        if p is None:
            # new user
            logging.info("Text: " + text)
            if text == '/help':
                reply(ISTRUZIONI)
            if text.startswith("/start"):
                p = person.addPerson(chat_id, name)
                reply("Ciao " + p.getFirstName() + ", " + "benvenuta/o!")
                init_user(p, name, last_name, username)
                restart(p)
                # state = -1 or -2
                tell_masters("New user: " + p.getFirstName())
            else:
                reply("Premi su /start se vuoi iniziare. "
                      "Se hai qualche domanda o suggerimento non esitare di contattarmi cliccando su @kercos")
        else:
            # known user
            person.updateUsername(p, username)
            if text.startswith("/start"):
                reply("Ciao " + p.getFirstName() + ", " + "ben ritrovata/o!")
                init_user(p, name, last_name, username)
                restart(p)
                # state = -1 or -2
            elif text=='/state':
              if p.state in STATES:
                  reply("You are in state " + str(p.state) + ": " + STATES[p.state])
              else:
                  reply("You are in state " + str(p.state))
            elif WORK_IN_PROGRESS and not p.isAdmin():
                reply(UNDER_CONSTRUCTION + " Il sistema è in aggiornamento, riprova più tardi.")
            elif text.startswith('/rec_'):
                sendVoiceLocationTranslationFromCommand(p, text, userInfo = p.isAdmin())
            elif text.startswith('/sendText') and p.isAdmin():
                dealWithsendTextCommand(p, text, markdown=False)
            elif p.state == -1:
                # INITIAL STATE
                if text in ['/help', BOTTONE_INFO]:
                    redirectToState(p, 8)
                elif text==BOTTONE_REGISTRA:
                    if p.location:
                        dealWithPlaceAndMicInstructions(p)
                    else:
                        reply("Questa è la tua prima registrazione: "
                              "è necessario che tu inserisca il luogo del dialetto che vuoi registrare.\n" +
                              ISTRUZIONI_POSIZIONE, kb = [[BOTTONE_ANNULLA]])
                        person.setState(p,-2)
                elif text==BOTTONE_ASCOLTA:
                    goToAscolta(p)
                    # state 30
                elif p.isAdmin():
                    if text == BOTTONE_ADMIN:
                        redirectToState(p, 9)
                    elif text == '/test':
                        reply('test')
                        #reply(geoUtils.getLocationTest())
                        #taskqueue.add(url='/worker', params={'key': key})
                        #geoUtils.test_Google_Map_Api()
                    elif text== '/infoCounts':
                        c = getInfoCount()
                        reply("Number of users: " + str(c))
                    elif text == '/restartUsers':
                        text = "Nuova interfaccia e nuove funzionalità :)\n" \
                               "Ora puoi inserire le località digitando il nome del posto (e.g, Perugia).\n" \
                               "Inoltre puoi cercare registrazioni in prossimità di un luogo.\n" \
                               "Buon ascolto e buona registrazione!"
                        deferred.defer(restartAllUsers, text) #'New interface :)')
                        #deferred.defer(restartTest, text) #'New interface :)')
                        logging.debug('restarted users')
                    elif text == '/voice':
                        sendVoiceFile(p.chat_id)
                    elif text == '/importVivaldi':
                        #logging.debug('nothing')
                        recording.importVivaldi()
                    elif text == '/countVivaldi':
                        c = recording.countVivaldi()
                        reply('Vivaldi recs: ' + str(c))
                    elif text == '/deleteVivaldi':
                        recording.deleteVivaldi()
                        reply('Deleted Vivaldi recs.')
                    elif text == '/remFormatVoice':
                        c = recording.removeFormatVoice()
                        reply("removed rec format voice: " + str(c))
                    elif text.startswith('/broadcast ') and len(text)>11:
                        msg = text[11:]
                        deferred.defer(broadcast, p.chat_id, msg, restart_user=False)
                    elif text.startswith('/restartBroadcast ') and len(text) > 18:
                        msg = text[18:]
                        deferred.defer(broadcast, p.chat_id, msg, restart_user=True)
                    elif text.startswith('/self ') and len(text)>6:
                        msg = text[6:]
                        reply(msg)
                    elif text=='/lastContributors':
                        count, namesString, recCommandsString = getLastContibutors(300)
                        msg = "Contributors: " + str(count) + "\nNames: " + namesString
                        reply(msg)
                    elif text=='/testWeeklyMessage':
                        msg = getWeeklyMessage()
                        reply(msg)
                    else:
                        reply('Scusa, capisco solo /help /start '
                              'e altri comandi segreti...')
                    #setLanguage(d.language)
                else:
                    reply("Scusa non capisco quello che hai detto.\n"
                          "Usa i pulsanti sotto o premi {} per avere informazioni.".format(BOTTONE_INFO))
            elif p.state == -2:
                # POSIZIONE
                if text == BOTTONE_ANNULLA:
                    restart(p, "Operazione annullata.")
                elif location!=None:
                    luogo = geoUtils.getComuneProvinciaFromCoordinates(location['latitude'], location['longitude'])
                    if luogo:
                        person.setLocation(p, location['latitude'], location['longitude'])
                        dealWithPlaceAndMicInstructions(p)
                    else:
                        reply("Non conosco la località inserita, prova ad essere più precisa/o.\n" +
                              ISTRUZIONI_POSIZIONE, kb=[[BOTTONE_INVIA_LOCATION], [BOTTONE_ANNULLA]])
                        logging.debug('Problem finding comune and provincia from coordinates {} {}'.format(
                            location['latitude'], location['longitude']))
                    #state 20
                elif text.startswith('('):
                    text_split = text[1:-1].split(",")
                    latitude = float(text_split[0])
                    longitude = float(text_split[1])
                    person.setLocation(p, latitude, longitude)
                    sendLocation(p.chat_id, latitude, longitude)
                    dealWithPlaceAndMicInstructions(p)
                    #state 20
                else:
                    place = geoUtils.getLocationFromName(text)
                    if place:
                        person.setLocation(p,place.latitude, place.longitude)
                        dealWithPlaceAndMicInstructions(p)
                         #state 20
                    else:
                        reply("Non conosco la località inserita, prova ad essere più precisa/o.\n" +
                              ISTRUZIONI_POSIZIONE, kb = [[BOTTONE_INVIA_LOCATION],[BOTTONE_ANNULLA]])
            elif p.state == 20:
                # REGISTRA
                if text == BOTTONE_INDIETRO:
                    restart(p, "Operazione annullata.")
                    # state = -1
                elif text == BOTTONE_CAMBIA_LUOGO:
                    reply("Ok, cambiamo il luogo.\n" +
                          ISTRUZIONI_POSIZIONE, kb = [[BOTTONE_INVIA_LOCATION],[BOTTONE_ANNULLA]])
                    person.setState(p,-2)
                    # state -2
                elif voice!=None:
                    reply("Ti preghiamo di ascoltare e confermare che la registrazione sia ben riuscita.",
                          kb=[['OK'],['REGISTRA DI NUOVO'],[BOTTONE_ANNULLA]])
                    file_id = voice['file_id']
                    #sendVoiceFileId(p.chat_id, file_id)
                    rec = recording.addRecording(p, file_id)
                    person.setLastRecording(p, rec)
                    person.setState(p, 21)
                # elif audio!=None:
                #     reply("Ti preghiamo di ascoltare e confermare che la registrazione sia ben riuscita.", kb=[['OK'],['REGISTRA DI NUOVO']])
                #     file_id = audio['file_id']
                #     #sendAudio(p.chat_id, file_id)
                #     rec = recording.addRecording(p, file_id, voice=False)
                #     person.setLastRecording(p, rec)
                #     person.setState(p, 21)
                # elif document!=None:
                #     file_id = document['file_id']
                #     reply("You have sent a doc")
                #     #sendVoice(p.chat_id, file_id)
                #     sendAudio(p.chat_id, file_id)
                #     restart(p)
                else:
                    reply(FROWNING_FACE + " Scusa non capisco quello che hai detto, devi inserire la registrazione tenendo premuto il microfono.")
            elif p.state == 21:
                # CONFIRM RECORDING
                if text == BOTTONE_ANNULLA:
                    person.removeLastRecording(p)
                    restart(p, "Operazione annullata.")
                    # state = -1
                elif text == 'OK':
                    msg = utility.unindent(
                        '''
                        Riteniamo utile avere una traduzione in italiano delle registrazione \
                        in modo da essere comprensibili da tutti gli utenti.\n
                        *Scrivi qua sotto* la traduzione della registrazione \
                        (in aggiunta puoi inserire la trascrizione in dialetto e il significato in caso si tratti di un proverbio)
                        '''
                    )
                    reply(msg, kb=[['Salta Traduzione']])
                    person.setState(p, 22)
                elif text == 'REGISTRA DI NUOVO':
                    person.removeLastRecording(p)
                    reply(MIC_INSTRUCTIONS, kb=[[BOTTONE_CAMBIA_LUOGO],[BOTTONE_ANNULLA]])
                    person.setState(p, 20)
                else:
                    reply(FROWNING_FACE + "Scusa non capisco quello che hai detto, premi *OK* per confermare la registrazione.")
            elif p.state == 22:
                # CHECK IF AVAILABLE FOR TRANSLATION
                if text == 'Salta Traduzione':
                    msg = "👍😀 Grazie per il tuo contributo!\n" \
                          "La registrazione è in attesa di approvazione, riceverai un messaggio a breve."
                    reply(msg)
                    sendNewRecordingNotice(p)
                    restart(p)
                elif text == '':
                    msg = "Input non valido. *Scrivi* qua sotto la traduzione in italiano della registrazione"
                    reply(msg, kb=[['Salta Traduzione']])
                    return
                else:
                    recording.addTranslation(p.last_recording_file_id, text)
                    msg = "👍😀 Grazie per il tuo contributo!\n" \
                          "La registrazione è in attesa di approvazione, riceverai un messaggio a breve."
                    reply(msg)
                    sendNewRecordingNotice(p)
                    restart(p)
            elif p.state == 30:
                if text == BOTTONE_INDIETRO:
                    restart(p)
                    # state = -1
                elif text== BOTTONE_INDOVINA_LUOGO:
                    dealWithRandomRecording(p)
                    # state 31
                elif text== BOTTONE_CERCA_LUOGO:
                    reply(ISTRUZIONI_POSIZIONE_SEARCH, kb = [[BOTTONE_INDIETRO]])
                    person.setState(p, 32)
                    # state 32
                elif text == BOTTONE_RECENTI:
                    getRecentRecordings(p)
                    person.setState(p, 33)
                    # state 33
                elif text == BOTTONE_TUTTE:
                    getAllRecordings(p)
                    person.setState(p, 33)
                    # state 33
            elif p.state == 31:
                # ASCOLTA - INDOVINA LUOGO
                if text == BOTTONE_INDIETRO:
                    restart(p)
                    # state = -1
                elif text=="ASCOLTA NUOVA REGISTRAZIONE":
                    dealWithRandomRecording(p)
                    # state 31
                elif location!=None:
                    dealWithGuessedLocation(p,location)
                else:
                    place = geoUtils.getLocationFromName(text)
                    if place:
                        guessed_loc = {'latitude': place.latitude, 'longitude': place.longitude}
                        dealWithGuessedLocation(p, guessed_loc)
                    else:
                        reply("Non conosco la località inserita, prova ad essere più precisa/o.\n" +
                              ISTRUZIONI_POSIZIONE_GUESS, kb = [[BOTTONE_ANNULLA]])
            elif p.state == 32:
                #ASCOLTA - RICERCA LUOGO
                sendWaitingAction(p.chat_id)
                if location!=None:
                    dealWithFindClosestRecording(p, location)
                elif text == BOTTONE_INDIETRO:
                    restart(p)
                else:
                    place = geoUtils.getLocationFromName(text)
                    if place:
                        loc = {'latitude': place.latitude, 'longitude': place.longitude}
                        dealWithFindClosestRecording(p, loc)
                    else:
                        reply("Non conosco la località inserita, prova ad essere più precisa/o.\n" +
                              ISTRUZIONI_POSIZIONE_SEARCH, kb = [[BOTTONE_ANNULLA]])
            elif p.state == 33:
                # REGISTRAZIONI RECENTI
                if text== BOTTONE_INDIETRO:
                    goToAscolta(p)
                else:
                    reply(FROWNING_FACE + "Scusa non capisco quello che hai detto.")
            else:
                logging.debug("Sending {0} to state {1}".format(p.getFirstName(), str(p.state)))
                repeatState(p, input=text)
            #else:
            #    reply("Se è verificato un problemino... segnalalo scrivendo a @kercos")

    def handle_exception(self, exception, debug_mode):
        logging.exception(exception)
        tell(key.FEDE_CHAT_ID, "❗ Detected Exception: " + str(exception), markdown=False)


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
#    ('/_ah/channel/connected/', DashboardConnectedHandler),
#    ('/_ah/channel/disconnected/', DashboardDisconnectedHandler),
    ('/infouser_weekly_all', InfoAllUsersWeeklyHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/get_webhook_info', GetWebhookInfo),
    ('/delete_webhook', DeleteWebhook),
    (key.WEBHOOK_PATH, WebhookHandler),
    ('/recordings/([^/]+)?', recording.DownloadRecordingHandler),
    ('/dynamicaudiomapdata.geojson', recording.ServeDynamicAudioGeoJsonFileHandler),
    ('/', RedirectMappa),
], debug=True)

possibles = globals().copy()
possibles.update(locals())
