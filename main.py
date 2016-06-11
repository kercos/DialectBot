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

import key
import emoij
import time_util

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.api import channel
from google.appengine.api import taskqueue
from google.appengine.ext import deferred

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
# ================================
# ================================

DASHBOARD_DIR_ENV = Environment(loader=FileSystemLoader('dashboard'), autoescape = True)

ISTRUZIONI =  \
"""
Sono @DialectBot, uno *strumento gratuito e aperto alla comunità* per condividere registrazioni nei diversi dialetti. \
Hai la possibilità di 👂 ascoltare gli audio che sono già stati inseriti o 🎙 registrarne di nuovi.

Se pensi di non parlare nessun dialetto specifico ti consigliamo \
di utilizzare questo strumento per registrare parenti, amici o persone \
che incontri quando ti capita di viaggiare tra paesini sperduti in Italia.

Per maggiori informazioni contatta @kercos

Aiutaci a far conoscere questo bot invitando altri amici e votandolo su \
[telegramitalia](telegramitalia.it/dialectbot) e su [storebot](telegram.me/storebot?start=dialectbot)

Buon 👂 ascolto e buona 🎙 registrazione a tutti!

"""

PLACE_AND_MIC_INSTRUCTIONS = \
"""
Il luogo della registrazione è impostato su: {0} \
(se il luogo non è corretto premi su 🔀🌍 *CAMBIA LUOGO*).

Quando sei pronta/o *pronuncia* 🗣 una frase nel dialetto del luogo inserito, ad esempio un proverbio o un modo di dire, \
*tenendo premuto il tasto del microfono* 🎙 (in basso).
"""

ISTRUZIONI_POSIZIONE = \
"""
Hai due modi per inserire il luogo del dialetto che vuoi registrare:
1) 🖊 *Scrivi* qua sotto il *nome del luogo* di cui vuoi inserire una registrazione (ad esempio Roma), oppure
2) 🌍 *Seleziona una posizione nella mappa* seguendo le seguenti istruzioni:
      📎 premi la graffetta in basso
      📍 invia una posizione dalla mappa (sii più preciso/a possibile).
"""

ISTRUZIONI_POSIZIONE_GUESS = \
"""
Hai due modi per indovinare il luogo della registrazione:
1) 🖊 *Scrivi* qua sotto il *nome del luogo* (ad esempio 'Palermo'), oppure
2) 🌍 *Seleziona una posizione nella mappa* seguendo le seguenti istruzioni:
      📎 premi la graffetta in basso
      📍 invia una posizione dalla mappa (sii più preciso/a possibile).
"""

ISTRUZIONI_POSIZIONE_SEARCH = \
"""
Hai due modi per cercare le registrazioni vicino ad un determinato luogo:
1) 🖊 *Scrivi* qua sotto il *nome del luogo* (ad esempio 'Palermo'), oppure
2) 🌍 *Seleziona una posizione nella mappa* seguendo le seguenti istruzioni:
      📎 premi la graffetta in basso
      📍 invia una posizione dalla mappa (sii più preciso/a possibile).
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
    20: 'Registra',
    21: 'Confirm recording',
    22: 'Ask for transcription',
    23: 'Deal with transcription answer',
    30: 'Ascolta',
    31: 'Indovina Luogo',
    32: 'Ricerca Luogo',
    0:   'Started',
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

BOTTONE_ANNULLA = CANCEL + " Annulla"
BOTTONE_INDIETRO = emoij.LEFTWARDS_BLACK_ARROW + ' ' + "Indietro"
BOTTONE_REGISTRA = MIC + " REGISTRA"
BOTTONE_ASCOLTA = EAR + " ASCOLTA"
BOTTONE_INVITA = SPEAKING_HEAD + " INVITA UN AMICO"
BOTTONE_INFO = INFO + " INFO"
BOTTONE_INDOVINA_LUOGO = WORLD + POINT_LEFT + " INDOVINA LUOGO"
BOTTONE_CERCA_LUOGO = SEARCH + " CERCA LUOGO"
BOTTONE_RECENTI = CALENDAR + " REGISTRAZIONI RECENTI"
BOTTONE_TUTTE = HUNDRED + " TUTTE LE REGISTRAZIONI"
BOTTONE_CAMBIA_LUOGO = "🔀🌍 CAMBIA LUOGO"

BOTTONE_CONTACT = {
    'text': "Invia il tuo contatto",
    'request_contact': True,
}

BOTTONE_LOCATION = {
    'text': "Invia la tua location",
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
    reply_txt += "Premi su 👂 *ASCOLTA* o 🎙 *REGISTRA* se vuoi ascoltare o registrare una frase in un dialetto."
    tell(p.chat_id, reply_txt, kb=[[BOTTONE_ASCOLTA,BOTTONE_REGISTRA], [BOTTONE_INVITA], [BOTTONE_INFO]])
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


def init_user(p, cmd, name, last_name, username):
    if (p.name.encode('utf-8') != name):
        p.name = name
        p.put()
    if (p.last_name.encode('utf-8') != last_name):
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

def broadcast(msg, restart_user=False):
    qry = Person.query().order(-Person.last_mod)
    count = 0
    for p in qry:
        if (p.enabled):
            count += 1
            if restart_user:
                restart(p)
            tell(p.chat_id, msg)
            sleep(0.100) # no more than 10 messages per second
    logging.debug('broadcasted to people ' + str(count))

def getRecentRecordings(p):
    recordings = ''
    qry = Recording.query().order(-Recording.date_time).fetch(8) #Recording.chat_id > 0
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
    count = 0
    qry = Recording.query(Recording.date_time > dateThreshold)
    for r in qry:
        if r.chat_id<=0:
            continue
        name = person.getPersonByChatId(r.chat_id).name
        names.add(name)
        count += 1
    namesString = ', '.join([x.encode('utf-8') for x in names])
    return count, namesString

def sendNewRecordingNotice(p):
    rec = recording.getRecording(p.last_recording_file_id)
    tell(key.FEDE_CHAT_ID, "New recording: /rec_" + str(rec.key.id()) + " from user: @" + p.getNameLastNameUserName())

def getInfoCount():
    c = Person.query().count()
    #msg = "Siamo ora " + str(c) + " persone iscritte a DialectBot! " \
    #      "Vogliamo crescere assieme! Invita altre persone ad unirsi!"
    return c

def tellmyself(p, msg):
    tell(p.chat_id, "Udiete udite... " + msg)

def tell_masters(msg):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg)

def tell_fede(msg):
    for i in range(100):
        tell(key.FEDE_CHAT_ID, "prova " + str(i))
        sleep(0.1)

def tell(chat_id, msg, kb=None, markdown=True, inlineKeyboardMarkup=False):

    replyMarkup = {}
    replyMarkup['resize_keyboard'] = True
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
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id==chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))


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

def sendLocation(chat_id, loc):
    try:
        resp = urllib2.urlopen(key.BASE_URL + 'sendLocation', urllib.urlencode({
            'chat_id': chat_id,
            'latitude': loc['latitude'],
            'longitude': loc['longitude'],
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
        tell(chat_id, "Traduzione: " + translation.encode('utf-8'))
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

def sendVoiceAndLocation(p, rec_command):
    digits = rec_command[5:]
    if utility.hasOnlyDigits(digits):
        rec_id = long(digits)
        rec = Recording.get_by_id(rec_id)
        if rec is None:
            tell(p.chat_id, 'No recording found!')
        else:
            tell(p.chat_id, 'Voice:')
            sendVoiceFileId(p.chat_id, rec.file_id)
            tell(p.chat_id, 'Location:')
            loc = {'latitude': rec.location.lat, 'longitude': rec.location.lon}
            sendLocation(p.chat_id, loc)
            sendTranslation(p.chat_id, rec)
    else:
        tell(p.chat_id, FROWNING_FACE + "Input non valido.")

def format_distance(dst):
    if (dst>=10):
        return str(round(dst, 0)) + " Km"
    if (dst>=1):
        return str(round(dst, 1)) + " Km"
    return str(int(dst*1000)) + " m"

def format_and_comment_distance(dst):
    fmt_dst = format_distance(dst)
    if (dst>=500):
        return fmt_dst + ". Sei molto lontano!"
    if (dst>=250):
        return fmt_dst + ". Puoi fare di meglio!"
    if (dst>=100):
        return fmt_dst + ". Non male!"
    if (dst>=50):
        return fmt_dst + ". Brava/o ci sei andata/o molto vicino!"
    if (dst>=15):
        return fmt_dst + ". Bravissima/o hai indovinato!"
    return fmt_dst + ". Wow, Strepitoso"


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
        tell(p.chat_id, "Ascolta l'audio seguente e inserisci la posizione geografica da dove credi che provenga")
        sendRecording(p.chat_id, randomRecording)
        person.setLastRecording(p,randomRecording)
        logging.debug("Last recording id: " + str(p.last_recording_file_id))
        tell(p.chat_id, ISTRUZIONI_POSIZIONE_GUESS, kb=[["ASCOLTA NUOVA REGISTRAZIONE"],[BOTTONE_INDIETRO]])
        person.setState(p, 31)

def dealWithGuessedLocation(p,guessed_loc):
    lat_guessed = guessed_loc['latitude']
    lon_guessed = guessed_loc['longitude']
    gold_loc = person.getLastRecordingLocation(p)
    lat_gold = gold_loc['latitude']
    lon_gold = gold_loc['longitude']
    logging.debug('Gold loc: ' + str(gold_loc))
    logging.debug('Guessed loc: ' + str(guessed_loc))
    luogo = '*' + geoUtils.getLocationFromPosition(lat_gold, lon_gold).address.encode('utf-8') + '*'
    #dist = geoUtils.HaversineDistance(lat_guessed, lon_guessed, lat_gold, lon_gold)
    dist = geoUtils.distance((lat_guessed, lon_guessed), (lat_gold, lon_gold))
    distFormatted = format_and_comment_distance(dist)
    tell(p.chat_id, "Distanza: " + distFormatted + "\n" + "Questo il luogo preciso: " + luogo)
    rec = recording.getRecordingCheckIfUrl(p.last_recording_file_id)
    sendLocation(p.chat_id, gold_loc)
    sendTranslation(p.chat_id, rec)

def dealWithPlaceAndMicInstructions(p):
    luogo = '*' + geoUtils.getLocationFromPosition(p.location.lat, p.location.lon).address.encode('utf-8') + '*'
    tell(p.chat_id, PLACE_AND_MIC_INSTRUCTIONS.format(luogo), kb=[[BOTTONE_CAMBIA_LUOGO],[BOTTONE_INDIETRO]])
    person.setState(p, 20)

def dealWithFindClosestRecording(p, location):
    rec = recording.getClosestRecording(location['latitude'], location['longitude'])
    if rec:
        tell(p.chat_id, "Trovata la seguente registrazione: ")
        sendRecording(p.chat_id, rec)
        loc = {'latitude': rec.location.lat, 'longitude': rec.location.lon}
        sendLocation(p.chat_id, loc)
        sendTranslation(p.chat_id, rec)
        luogo = '*' + geoUtils.getLocationFromPosition(rec.location.lat, rec.location.lon).address.encode('utf-8') + '*'
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
        url = self.request.get('url')
        if url:
            self.response.write(
                json.dumps(json.load(urllib2.urlopen(key.BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))

class InfoAllUsersWeeklyHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        msg = getWeeklyMessage()
        broadcast(msg, restart_user=True)

def getWeeklyMessage():
    people_count = getInfoCount()
    contr_count, contr_namesString = getLastContibutors(7)
    msg = "Siamo ora " + str(people_count) + " persone iscritte a DialectBot!\n\n"
    if contr_count > 0:
        if contr_count == 1:
            msg += "Nell'ultima settimana abbiamo ricevuto una registrazione! " \
                   "Un grande ringraziamento a " + contr_namesString + '! ' + CLAPPING_HANDS
        else:
            msg += "Nell'ultima settimana abbiamo ricevuto " + str(contr_count) + \
                   " registrazioni! " \
                   "Un grande ringraziamento a " + contr_namesString + '! ' + CLAPPING_HANDS * contr_count
    else:
        msg += "Purtroppo questa settimana non abbiamo avuto nessun nuovo contributo " + FROWNING_FACE

    msg += "\n\nAiutaci a crescere: aggiungi nuove registrazioni del tuo dialetto tramite il bot " \
           "e invita altre persone ad unirsi! " + SMILY
    return msg

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
            tell(chat_id, msg, kb, markdown, inlineKeyboardMarkup)

        p = ndb.Key(Person, str(chat_id)).get()

        if p is None:
            # new user
            logging.info("Text: " + text)
            if text == '/help':
                reply(ISTRUZIONI)
            if text.startswith("/start"):
                tell_masters("New user: " + name)
                p = person.addPerson(chat_id, name)
                reply("Ciao " + name + ", " + "benvenuta/o!")
                init_user(p, text, name, last_name, username)
                restart(p)
                # state = -1 or -2
            else:
                reply("Premi su /start se vuoi iniziare. "
                      "Se hai qualche domanda o suggerimento non esitare di contattarmi cliccando su @kercos")
        else:
            # known user
            person.updateUsername(p, username)
            if text.startswith("/start"):
                reply("Ciao " + name + ", " + "ben ritrovata/o!")
                init_user(p, text, name, last_name, username)
                restart(p)
                # state = -1 or -2
            elif text=='/state':
              if p.state in STATES:
                  reply("You are in state " + str(p.state) + ": " + STATES[p.state])
              else:
                  reply("You are in state " + str(p.state))
            elif p.state == -1:
                # INITIAL STATE
                if text in ['/help', BOTTONE_INFO]:
                    reply(ISTRUZIONI)
                elif text == BOTTONE_INVITA:
                    reply('Inoltra il seguente messaggio a parenti e amici 😊')
                    reply(MESSAGE_FOR_FRIENDS)
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
                elif chat_id in key.MASTER_CHAT_ID:
                    if text == '/test':
                        reply('test')
                        #reply(geoUtils.getLocationTest())
                        #taskqueue.add(url='/worker', params={'key': key})
                        #geoUtils.test_Google_Map_Api()
                    elif text == '/testContactAndLocation':
                        reply("Test contatto e location", kb=[[BOTTONE_CONTACT], [BOTTONE_LOCATION]])
                    elif text == '/testInlineKeyboard':
                        reply("Test contatto e location", kb=[[BOTTONE_CALLBACK1,BOTTONE_CALLBACK2],[BOTTONE_CALLBACK3]], inlineKeyboardMarkup=True)
                    elif text == '/testUnicode':
                        txt = geoUtils.getLocationTest().address.encode('utf-8')
                        #txt = "Questa è una frase con unicode"
                        reply(txt + " " + str(type(txt)) )
                    elif text== '/infocount':
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
                    elif text == '/deleteApproxLoc':
                        recording.deleteLocationApprox()
                    elif text == '/initApproxLoc':
                        recording.initializeApproxLocations()
                        reply('Reinitialized approx locations. ')
                    elif text.startswith('/rec_'):
                        sendVoiceAndLocation(p, text)
                    elif text == '/remFormatVoice':
                        c = recording.removeFormatVoice()
                        reply("removed rec format voice: " + str(c))
                    elif text.startswith('/broadcast ') and len(text)>11:
                        msg = text[11:]
                        deferred.defer(broadcast, msg, restart_user=False)
                    elif text.startswith('/restartBroadcast ') and len(text) > 18:
                        msg = text[18:]
                        deferred.defer(broadcast, msg, restart_user=True)
                    elif text.startswith('/self ') and len(text)>6:
                        msg = text[6:]
                        reply(msg)
                    elif text=='/lastContributors':
                        count, namesString = getLastContibutors(300)
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
                          "Usa i pulsanti sotto o premi HELP per avere informazioni.")
            elif p.state == -2:
                # POSIZIONE
                if text == BOTTONE_ANNULLA:
                    restart(p, "Operazione annullata.")
                elif location!=None:
                    person.setLocation(p,location)
                    luogo = geoUtils.getLocationFromPosition(p.location.lat, p.location.lon).address.encode('utf-8')
                    dealWithPlaceAndMicInstructions(p)
                    #state 20
                elif text.startswith('('):
                    text_split = text[1:-1].split(",")
                    loc = {'latitude': float(text_split[0]), 'longitude': float(text_split[1])}
                    person.setLocation(p,loc)
                    sendLocation(p.chat_id, loc)
                    dealWithPlaceAndMicInstructions(p)
                    #state 20
                else:
                    place = geoUtils.getLocationFromName(text)
                    if place:
                        loc = {'latitude': place.latitude, 'longitude': place.longitude}
                        person.setLocation(p,loc)
                        dealWithPlaceAndMicInstructions(p)
                         #state 20
                    else:
                        reply("Non conosco la località inserita, prova ad essere più precisa/o.\n" +
                              ISTRUZIONI_POSIZIONE, kb = [[BOTTONE_ANNULLA]])
            elif p.state == 20:
                # REGISTRA
                if text == BOTTONE_INDIETRO:
                    restart(p, "Operazione annullata.")
                    # state = -1
                elif text == BOTTONE_CAMBIA_LUOGO:
                    reply("Ok, cambiamo il luogo. " +
                          ISTRUZIONI_POSIZIONE, kb = [[BOTTONE_ANNULLA]])
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
                    reply(FROWNING_FACE + " Scusa non capisco quello che hai detto.")
            elif p.state == 21:
                # CONFIRM RECORDING
                if text == BOTTONE_ANNULLA:
                    restart(p, "Operazione annullata.")
                    # state = -1
                elif text == 'OK':
                    reply("Potresti lasciare una traduzione in italiano della registrazione?", kb=[['SI','NO']])
                    person.setState(p, 22)
                elif text == 'REGISTRA DI NUOVO':
                    person.removeLastRecording(p)
                    reply("Quando sei pronta/o pronuncia una frase nel dialetto del luogo inserito, ad esempio un proverbio o un modo di dire, "
                          "tenendo premuto il tasto del microfono.", kb=[[BOTTONE_CAMBIA_LUOGO],[BOTTONE_ANNULLA]])
                    person.setState(p, 20)
                else:
                    reply(FROWNING_FACE + "Scusa non capisco quello che hai detto.")
            elif p.state == 22:
                # CHECK IF AVAILABLE FOR TRANSLATION
                if text == 'SI':
                    reply("*Scrivi* qua sotto la traduzione in italiano della registrazione",
                          kb=[[BOTTONE_ANNULLA]])
                    person.setState(p, 23)
                elif text == 'NO':
                    reply("Grazie per il tuo contributo!")
                    #sendNewRecordingNotice(p)
                    restart(p)
                else:
                    reply(FROWNING_FACE + "Scusa non capisco quello che hai detto.")
            elif p.state == 23:
                if text == '':
                    reply("Input non valido. *Scrivi* qua sotto la traduzione in italiano della registrazione",
                          kb=[[BOTTONE_ANNULLA]])
                    return
                elif text == BOTTONE_ANNULLA:
                    text = ''
                # INSERT TRANSLATION
                recording.addTranslation(p.last_recording_file_id, text)
                reply("Grazie per il tuo contributo!")
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
                              ISTRUZIONI_POSIZIONE, kb = [[BOTTONE_ANNULLA]])
            elif p.state == 32:
                #ASCOLTA - RICERCA LUOGO
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
                elif text.startswith('/rec_'):
                    sendVoiceAndLocation(p, text)
                else:
                    reply(FROWNING_FACE + "Scusa non capisco quello che hai detto.")
            else:
                reply("Se è verificato un problemino... segnalalo scrivendo a @kercos")

app = webapp2.WSGIApplication([
    ('/me', MeHandler),
#    ('/_ah/channel/connected/', DashboardConnectedHandler),
#    ('/_ah/channel/disconnected/', DashboardDisconnectedHandler),
    ('/infouser_weekly_all', InfoAllUsersWeeklyHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
    ('/recordings/([^/]+)?', recording.DownloadRecordingHandler),
    ('/dynamicaudiomapdata.geojson', recording.ServeDynamicAudioGeoJsonFileHandler),
], debug=True)
