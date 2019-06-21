# -*- coding: utf-8 -*-

# Set up requests
# see https://cloud.google.com/appengine/docs/standard/python/issue-requests#issuing_an_http_request
import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()

import requests
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.contrib.appengine.AppEnginePlatformWarning
)

import json
import jsonUtil
import logging
import person
from person import Person
from time import sleep
import recording
from recording import Recording
import geoUtils

import main_telegram
from main_telegram import send_message, send_location, send_voice, sendWaitingAction

import key
import emoij
import time_util

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext.db import datastore_errors

import webapp2

import utility


# ================================
WORK_IN_PROGRESS = False
# ================================


# ================================
# ================================
# ================================

ISTRUZIONI =  \
"""
Sono @DialettiBot, uno *strumento gratuito e aperto alla comunità* per condividere registrazioni nei diversi dialetti. \
Hai la possibilità di 👂 ascoltare gli audio che sono già stati inseriti o 🗣 registrarne di nuovi.

Se pensi di non parlare nessun dialetto puoi comunque \
utilizzare questo strumento per registrare parenti, amici o persone \
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
Ciao, ho scoperto @DialettiBot, un tool gratuito e aperto alla comunità \
per ascoltare e registrare i dialetti italiani. \
Provalo premendo su @DialettiBot!
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
    send_message(p.chat_id, reply_txt, kb=[[BOTTONE_ASCOLTA,BOTTONE_REGISTRA], second_row_buttons])
    person.setState(p, -1)

def restartAllUsers(msg):
    qry = Person.query()
    count = 0
    for p in qry:
        if p.enabled:
            restart(p)
            send_message(p.chat_id, msg)
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

def broadcast(sender_chat_id, msg, restart_user=False, curs=None, enabledCount = 0):

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
            if restart_user:
                restart(p)
            if send_message(p.chat_id, msg, sleepDelay=True, url_api=key.DEFAULT_BROADCAST_API_URL):
                enabledCount += 1

    if more:
        deferred.defer(broadcast, sender_chat_id, msg, restart_user, next_curs, enabledCount)
    else:
        total = Person.query().count()
        disabled = total - enabledCount
        msg_debug = BROADCAST_COUNT_REPORT.format(str(total), str(enabledCount), str(disabled))
        send_message(sender_chat_id, msg_debug)

def getRecentRecordings(p):
    recordings = ''
    qry = Recording.query(Recording.approved == recording.REC_APPROVED_STATE_TRUE).order(-Recording.date_time).fetch(8)
    for r in qry:
        name = person.getPersonByChatId(r.chat_id).name.encode('utf-8')
        recordings += '/rec_' + str(r.key.id()) + ' - ' + name + ' - ' + str(r.date_time.date()) + '\n'
    send_message(p.chat_id,
         "ULTIME REGISTRAZIONI:\n\n" + recordings +
         "\nPremi su uno dei link sopra per ascoltare la registrazione corrispondente.",
         kb=[[BOTTONE_INDIETRO]], markdown=False)

def getAllRecordings(p):
    recordings = ''
    qry = Recording.query(Recording.chat_id > 0)
    for r in qry:
        name = person.getPersonByChatId(r.chat_id).name
        recordings += '/rec_' + str(r.key.id()) + ' - ' + name + ' - ' + str(r.date_time.date()) + '\n'
    send_message(p.chat_id,
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
    send_message(key.FEDE_CHAT_ID, "New recording: /rec_" + str(rec.key.id()) + " from user {0}: {1}".format(
        str(p.chat_id), p.getUserInfoString()), markdown=False)

def tellmyself(p, msg):
    send_message(p.chat_id, "Udiete udite... " + msg)

def tell_masters(msg, markdown=False, one_time_keyboard=False):
    for id in key.MASTER_CHAT_ID:
        send_message(id, msg, markdown=markdown, one_time_keyboard = one_time_keyboard, sleepDelay=True)

def tell_fede(msg):
    for i in range(100):
        send_message(key.FEDE_CHAT_ID, "prova " + str(i))
        sleep(0.1)

def tell_person(chat_id, msg, markdown=False):
    send_message(chat_id, msg, markdown=markdown)
    p = ndb.Key(Person, str(chat_id)).get()
    if p and p.enabled:
        return True
    return False

def sendTranslation(chat_id, rec):
    translation = rec.translation
    if translation:
        send_message(chat_id, "Spiegazione: " + translation.encode('utf-8'))
    else:
        send_message(chat_id, "Nessuna traduzione.")


def send_voiceLocationTranslationFromCommand(p, rec_command, userInfo = False):
    digits = rec_command[5:]
    if utility.hasOnlyDigits(digits):
        rec_id = long(digits)
        rec = Recording.get_by_id(rec_id)
        if rec is None:
            send_message(p.chat_id, 'No recording found!')
        else:
            send_voiceLocationTranslation(p, rec, userInfo=userInfo)
    else:
        send_message(p.chat_id, FROWNING_FACE + "Input non valido.")

def send_voiceLocationTranslation(p, rec, userInfo = False):
    if userInfo:
        user = person.getPersonByChatId(rec.chat_id)
        send_message(p.chat_id, 'Registrazione eseguita da: {}'.format(user.getFirstName()))
    send_message(p.chat_id, 'Audio:')
    send_voice(p.chat_id, rec)
    msg = 'Luogo: ' + geoUtils.getComuneProvinciaFromCoordinates(rec.location.lat, rec.location.lon)
    send_message(p.chat_id, msg)
    send_location(p.chat_id, rec.location.lat, rec.location.lon)
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
# ================================
# ================================

def dealWithRandomRecording(p):
    randomRecording = recording.getRandomRecording()
    if not randomRecording:
        send_message(p.chat_id, "Scusa, non abbiamo altre registrazioni disponibili, chidi ai tuoi amici di inserirne altre", kb=[[BOTTONE_ANNULLA]])
        restart(p)
    else:
        send_message(p.chat_id, "Ascolta l'audio seguente e prova ad indovinare da dove proviene 😀")
        send_voice(p.chat_id, randomRecording)
        person.setLastRecording(p,randomRecording)
        logging.debug("Last recording id: " + str(p.last_recording_file_id))
        send_message(p.chat_id, ISTRUZIONI_POSIZIONE_GUESS, kb=[["ASCOLTA NUOVA REGISTRAZIONE"],[BOTTONE_INDIETRO]])
        person.setState(p, 31)

def dealWithGuessedLocation(p,guessed_loc):
    lat_guessed = guessed_loc['latitude']
    lon_guessed = guessed_loc['longitude']
    lat_gold, lon_gold  = person.getLastRecordingLatLonLocation(p)
    logging.debug('Gold loc: ' + str((lat_gold, lon_gold)))
    logging.debug('Guessed loc: ' + str(guessed_loc))
    luogo = geoUtils.getComuneProvinciaFromCoordinates(lat_gold, lon_gold)
    #dist = geoUtils.HaversineDistance(lat_guessed, lon_guessed, lat_gold, lon_gold)
    dist = geoUtils.distance((lat_guessed, lon_guessed), (lat_gold, lon_gold))
    distFormatted = format_and_comment_distance(dist)
    msg = "Distanza: " + distFormatted
    if luogo:
        msg += '\n' + "Questo il luogo preciso: *{}*".format(luogo)
    send_message(p.chat_id, msg)
    rec = recording.getRecordingCheckIfUrl(p.last_recording_file_id)
    send_location(p.chat_id, lat_gold, lon_gold)
    sendTranslation(p.chat_id, rec)

def dealWithPlaceAndMicInstructions(p):
    lat, lon = p.location.lat, p.location.lon
    luogo = geoUtils.getComuneProvinciaFromCoordinates(lat, lon)
    if luogo==None:
        send_message(p.chat_id, "Il luogo inserito non è stato riconosciuto, riprova.")
        send_message(key.FEDE_CHAT_ID, "A user inserted a unrecognized location: {},{}".format(lat, lon))
        send_location(key.FEDE_CHAT_ID, lat, lon)
    else:
        luogo = '*{}*'.format(luogo)
        instructions = PLACE_INSTRUCTIONS.format(luogo) + MIC_INSTRUCTIONS
        send_message(p.chat_id, instructions, kb=[[BOTTONE_CAMBIA_LUOGO],[BOTTONE_INDIETRO]])
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
        send_message(p.chat_id, "Trovata la seguente registrazione: ")
        send_voice(p.chat_id, rec)
        send_location(p.chat_id, rec.location.lat, rec.location.lon)
        sendTranslation(p.chat_id, rec)
        comune_provincia = geoUtils.getComuneProvinciaFromCoordinates(rec.location.lat, rec.location.lon)
        dst = geoUtils.distance((location['latitude'], location['longitude']), (rec.location.lat, rec.location.lon))
        if comune_provincia:
            luogo = '*' + comune_provincia + '*'
            send_message(p.chat_id, "Luogo della registrazione: " + luogo +
                 ". La distanza dal luogo inserito è di: " + format_distance(dst) + ".")
        else:
            send_message(p.chat_id, "La distanza dal luogo inserito è di: " + format_distance(dst) + ".")
            logging.warning("Can't find luogo for registrazione id = {}".format(rec.key.id()))
        send_message(p.chat_id, "Se vuoi cercare un'altra registrazione inserisci una nuova località altrimenti premi 'Indietro'.")

    else:
        send_message(p.chat_id, "Non ho trovato nessuna registrazione nelle vicinanze della posizione inserita. Riprova.\n" +
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
    send_message(p.chat_id, ASCOLTA_MSG,
         kb=[[BOTTONE_INDOVINA_LUOGO, BOTTONE_CERCA_LUOGO], [BOTTONE_RECENTI], [BOTTONE_INDIETRO]])
    person.setState(p, 30)

#BOTTONE_TUTTE

# ================================
# HANDLERS
# ================================

class RedirectMappa(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(20)
        self.redirect("http://dialectbot.appspot.com/audiomap/mappa.html")

class InfoAllUsersMonthlyHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(20)
        msg = getMonthlyMessage()
        broadcast(key.FEDE_CHAT_ID, msg, restart_user=True)

def getMonthlyMessage():
    people_count = person.getPeopleCount()
    contr_count, contr_namesString, recCommandsString = getLastContibutors(31)
    msg = "Siamo ora " + str(people_count) + " persone iscritte a @DialettiBot!\n\n"
    if contr_count > 0:
        if contr_count == 1:
            msg += utility.unindent(
                """
                Nell'ultimo mese abbiamo ricevuto una registrazione!
                Un grande ringraziamento a *{}*! {}\n
                Se vuoi ascoltarla premi su questo comando:\n{}
                """.format(contr_namesString, CLAPPING_HANDS, recCommandsString)
            )
        else:
            msg += utility.unindent(
                """
                Nell'ultimo mese abbiamo ricevuto {} registrazioni!
                Un grande ringraziamento a *{}*! {}\n
                Se vuoi ascoltarle premi su questi comandi:\n{}
                """.format(contr_count, contr_namesString, CLAPPING_HANDS*contr_count, recCommandsString)
            )
    else:
        msg += "Purtroppo questo mese non abbiamo ricevuto nessuna nuova registrazione " + FROWNING_FACE

    msg += "\n\nSul sito http://dialectbot.appspot.com potrai " \
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
        send_message(p.chat_id, "Si è verificato un problema (" + methodName +
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

        send_message(p.chat_id, ISTRUZIONI, kb)
    else:
        if input == '':
            send_message(p.chat_id, "Input non valido.")
        elif input == BOTTONE_INVITA:
            send_message(p.chat_id, "Inoltra il seguente messaggio a parenti e amici 😊")
            sendWaitingAction(p.chat_id)
            sleep(3)
            send_message(p.chat_id, MESSAGE_FOR_FRIENDS, kb = [[BOTTONE_INDIETRO]])
        elif input == BOTTONE_INDIETRO:
            restart(p)
        else:
            send_message(p.chat_id, FROWNING_FACE + " Scusa, non capisco quello che hai detto.")


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

        send_message(p.chat_id, reply_txt, kb)
    else:
        if input == '':
            send_message(p.chat_id, "Input non valido.")
        elif input == BOTTONE_APPROVA_REGISTRAZIONI:
            redirectToState(p, 91)
        elif input == BOTTONE_INDIETRO:
            restart(p)
        else:
            send_message(p.chat_id, FROWNING_FACE + " Scusa, non capisco quello che hai detto.")

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
            send_voiceLocationTranslation(p, rec, userInfo=True)
            kb = [
                [BOTTONE_APPROVA, BOTTONE_DISAPPROVA],
                [BOTTONE_INDIETRO]
            ]
            send_message(p.chat_id, "Approvi questa registrazione?", kb)
        else:
            kb = [[BOTTONE_INDIETRO]]
            send_message(p.chat_id, "Non c'è nessuna registrazione da approvare", kb)
    else:
        if input == '':
            send_message(p.chat_id, "Input non valido.")
        elif input == BOTTONE_APPROVA:
            rec = recording.getRecording(p.last_recording_file_id)
            send_message(rec.chat_id, USER_MSG.format('', str(rec.key.id())), markdown=False)
            send_message(p.chat_id, "Registrazione approvata!")
            rec.approve(recording.REC_APPROVED_STATE_TRUE)
            recording.appendRecordingInGeoJsonStructure(rec)
            sleep(2)
            repeatState(p)
        elif input == BOTTONE_DISAPPROVA:
            rec = recording.getRecording(p.last_recording_file_id)
            send_message(rec.chat_id, USER_MSG.format(' NON ', str(rec.key.id())), markdown=False)
            send_message(p.chat_id, "Registrazione NON approvata! "
                            "Se vuoi mandare maggiori info scrivi /sendText {0} text".format(str(rec.chat_id)))
            rec.approve(recording.REC_APPROVED_STATE_FALSE)
            sleep(2)
            repeatState(p)
        elif input == BOTTONE_INDIETRO:
            redirectToState(p, 9)
        else:
            send_message(p.chat_id, FROWNING_FACE + " Scusa, non capisco quello che hai detto.")


# ================================
# ================================
# ================================

def dealWithsendTextCommand(p, sendTextCommand, markdown=False):
    split = sendTextCommand.split()
    if len(split)<3:
        send_message(p.chat_id, 'Commands should have at least 2 spaces')
        return
    if not split[1].isdigit():
        send_message(p.chat_id, 'Second argumnet should be a valid chat_id')
        return
    id = int(split[1])
    sendTextCommand = ' '.join(split[2:])
    if tell_person(id, sendTextCommand, markdown=markdown):
        user = person.getPersonByChatId(id)
        send_message(p.chat_id, 'Successfully sent text to ' + user.getFirstName())
    else:
        send_message(p.chat_id, 'Problems in sending text')


# ================================
# ================================
# ================================


class DialectWebhookHandler(webapp2.RequestHandler):
    def post(self):
        body = jsonUtil.json_loads_byteified(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))
        if 'message' not in body:
            return
        message = body['message']
        if "chat" not in message:
            return
        chat = message['chat']
        chat_id = chat['id']
        msg = "Ciao, ci siamo trasferiti su @DialettiBot!"
        send_message(chat_id, msg, remove_keyboard=True, url_api=key.DIALECT_API_URL)


class DialettiWebhookHandler(webapp2.RequestHandler):

    def post(self):
        body = jsonUtil.json_loads_byteified(self.request.body)
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
        text = message.get('text', "")
        name = chat["first_name"]
        last_name = chat.get("last_name", "-")
        username = chat.get("username", "-")
        location = message.get("location", None)
        voice = message.get("voice", None)
        #audio = message.get("audio", None)
        #document = message.get("document", None)

        logging.debug("Received input from {}. Text={} Location={}".format(chat_id, text, location))

        def reply(msg=None, kb=None, markdown=True, inline_keyboard=False):
            send_message(chat_id, msg, kb=kb, markdown=markdown, inline_keyboard=inline_keyboard)

        p = person.getPersonByChatId(chat_id)

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
                send_voiceLocationTranslationFromCommand(p, text, userInfo = p.isAdmin())
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
                    elif text == '/infoCounts':
                        c = person.getPeopleCount()
                        reply("Number of users: " + str(c))
                    elif text == '/restartUsers':
                        text = "Nuova interfaccia e nuove funzionalità :)\n" \
                               "Ora puoi inserire le località digitando il nome del posto (e.g, Perugia).\n" \
                               "Inoltre puoi cercare registrazioni in prossimità di un luogo.\n" \
                               "Buon ascolto e buona registrazione!"
                        deferred.defer(restartAllUsers, text) #'New interface :)')
                        #deferred.defer(restartTest, text) #'New interface :)')
                        logging.debug('restarted users')
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
                    elif text == '/stats':
                        msg = recording.getRecodingsStats()
                        send_message(p.chat_id, msg, markdown=False)
                        msg = "People count: {}".format(person.getPeopleCount())
                        send_message(p.chat_id, msg, markdown=False)
                    elif text.startswith('/echo ') and len(text)>6:
                        msg = text[6:]
                        reply(msg)
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
                    elif text=='/testMonthlyMessage':
                        msg =   getMonthlyMessage()
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
                    logging.debug('User sending location: {}, {}'.format(location['latitude'], location['longitude']))
                    luogo = geoUtils.getComuneProvinciaFromCoordinates(location['latitude'], location['longitude'])
                    logging.debug('Detected luogo: {}'.format(luogo))
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
                    send_location(p.chat_id, latitude, longitude)
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
                    reply("Bene! 😉\n"
                          "Ora riascolta la registrazione e conferma su ✅ OK "
                          "se la registrazione è ben riuscita o premi su 🎙 REGISTRA DI NUOVO per"
                          "effettuare un'altra registrazione.",
                          kb=[['✅ OK'],['🎙 REGISTRA DI NUOVO'],[BOTTONE_ANNULLA]])
                    file_id = voice['file_id']
                    #send_voice(p.chat_id, file_id)
                    rec = recording.addRecording(p, file_id)
                    person.setLastRecording(p, rec)
                    person.setState(p, 21)
                else:
                    reply(FROWNING_FACE + " Scusa non capisco quello che hai detto, devi inserire la registrazione tenendo premuto il microfono.")
            elif p.state == 21:
                # CONFIRM RECORDING
                if text == BOTTONE_ANNULLA:
                    person.removeLastRecording(p)
                    restart(p, "Operazione annullata.")
                    # state = -1
                elif text == '✅ OK':
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
                elif text == '🎙 REGISTRA DI NUOVO':
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
                else:
                    msg = "Input non valido. Usa i pulsanti qua sotto."
                    reply(msg)
                    return
            elif p.state == 31:
                # ASCOLTA - INDOVINA LUOGO
                if text in [BOTTONE_INDIETRO, BOTTONE_ANNULLA]:
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
                              ISTRUZIONI_POSIZIONE_SEARCH, kb = [[BOTTONE_INDIETRO]])
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
        send_message(key.FEDE_CHAT_ID, "❗ Detected Exception: " + str(exception), markdown=False)


app = webapp2.WSGIApplication([
    ('/infouser_monthly_all', InfoAllUsersMonthlyHandler),
    ('/me', main_telegram.MeHandler), #?botname=dialectbot|dialettibot
    ('/set_webhook', main_telegram.SetWebhookHandler), #?botname=dialectbot|dialettibot
    ('/get_webhook_info', main_telegram.GetWebhookInfo), #?botname=dialectbot|dialettibot
    ('/delete_webhook', main_telegram.DeleteWebhook), #?botname=dialectbot|dialettibot
    (key.DIALECT_WEBHOOK_PATH, DialectWebhookHandler),
    (key.DIALETTI_WEBHOOK_PATH, DialettiWebhookHandler),
    ('/recordings/([^/]+)?', recording.DownloadRecordingHandler),
    ('/dynamicaudiomapdata.geojson', recording.ServeDynamicAudioGeoJsonFileHandler),
    ('/', RedirectMappa),
], debug=True)

possibles = globals().copy()
possibles.update(locals())
