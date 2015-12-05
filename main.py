#import json
import json
import logging
import urllib
import urllib2
import datetime
from datetime import datetime
from datetime import timedelta
from time import sleep
import date_util
# import requests

import key
import emoij

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

from jinja2 import Environment, FileSystemLoader

# ================================
# ================================
# ================================

BASE_URL = 'https://api.telegram.org/bot' + key.TOKEN + '/'

DASHBOARD_DIR_ENV = Environment(loader=FileSystemLoader('dashboard'), autoescape = True)
tell_completed = False

ISTRUZIONI =  "Istruzioni OpenGarden, da inserire..."

AVVERTENZE = "Avvertenze OpenGarden, da inserire..."


STATES = {
    -4: 'Posizione',
    -3: 'Posizione/Contatto',
    -2: 'Settings',
    -1: 'Initial',
    0:   'Started',
}

BOTTONE_ANNULLA = emoij.NOENTRY + " Annulla"

PRODOTTI = [['Caki','Carote']]
PRODOTTI_ANNULLA = copy.deepcopy(PRODOTTI)
PRODOTTI_ANNULLA.append([BOTTONE_ANNULLA])
PRODOTTI_FLAT = list(itertools.chain(*PRODOTTI))

"""
PRODOTTI = [
    ['Caki','Castagne','Wiwi'],
    ['Mele','Noci','Pere'],
    ['Barbabietole','Bietola'],
    ['Broccoli', 'Carote','Cavolfiori'],
    ['Carciofi','Cappuccio','Cipolla'],
    ['Finocchio','Insalata','Porri'],
    ['Prezzemolo','Radicchio','Ravanello'],
    ['Spinaci','Zucca']
]
"""

# ================================
# ================================
# ================================

class Counter(ndb.Model):
    name = ndb.StringProperty()
    counter = ndb.IntegerProperty()


COUNTERS = []

def resetCounter():
    for name in COUNTERS:
        c = Counter.get_or_insert(str(name))
        c.name = name
        c.counter = 0
        c.put()

def increaseCounter(c, i):
    entry = Counter.query(Counter.name == c).get()
    c = entry.counter
    c = (c+i)
    entry.counter = c
    entry.put()
    return c


# ================================
# ================================
# ================================


class DateCounter(ndb.Model):
    date = ndb.DateProperty(auto_now_add=True)
    people_counter = ndb.IntegerProperty()

def addPeopleCount():
    p = DateCounter.get_or_insert(str(datetime.now()))
    p.people_counter = Person.query().count()
    p.put()
    return p

# ================================
# ================================
# ================================


class Product(ndb.Model):
    chat_id = ndb.IntegerProperty(indexed=True)
    product = ndb.StringProperty(indexed=True)
    person_name = ndb.StringProperty()
    entry_date = ndb.DateTimeProperty(auto_now=True)
    location = ndb.GeoPtProperty()
    contact = ndb.StringProperty()

def getProduct(chat_id, product):
    key = str(chat_id) + '_' + product
    product = ndb.Key(Product, key).get()
    return product

def addProduct(chat_id, product, person_name, location, contact):
    p = Product.get_or_insert(str(chat_id) + '_' + product)
    p.chat_id = chat_id
    p.product = product
    p.person_name = person_name
    p.location = location
    p.contact = contact
    p.put()
    return p

def getListProducts(product, p):
    result = []
    qry = Product.query(Product.product==product)
    for r in qry:
        if (r.chat_id!=p.chat_id):
            distance = HaversineDistance(p.location,r.location)
            result.append([r.person_name, distance, r.contact])
    sort_table(result, 1)
    return result

def format_distance(dst):
    if (dst>=100):
        return str(round(dst, 0)) + " km"
    if (dst>=10):
        return str(round(dst, 1)) + " km"
    if (dst>=1):
        return str(round(dst, 2)) + " km"
    return str(round(dst*1000, 0)) + " m"

def sort_table(table, col=0):
    return sorted(table, key=operator.itemgetter(col))

def HaversineDistance(loc1, loc2):
    """Method to calculate Distance between two sets of Lat/Lon."""
    lat1 = loc1.lat
    lon1 = loc1.lon
    lat2 = loc2.lat
    lon2 = loc2.lon
    earth = 6371 #Earth's Radius in Kms.

    #Calculate Distance based in Haversine Formula
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = earth * c
    return d

# ================================
# ================================
# ================================


class Person(ndb.Model):
    chat_id = ndb.IntegerProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty(default='-')
    username = ndb.StringProperty(default='-')
    state = ndb.IntegerProperty(default=-1, indexed=True)
    last_mod = ndb.DateTimeProperty(auto_now=True)
    location = ndb.GeoPtProperty()
    contact = ndb.StringProperty()
    enabled = ndb.BooleanProperty(default=True)


def addPerson(chat_id, name):
    p = Person.get_or_insert(str(chat_id))
    p.name = name
    p.chat_id = chat_id
    p.put()
    return p

def setState(p, state):
    p.state = state
    p.put()

def restart(person, txt=None):
    reply_txt = (txt + '\n') if txt!=None else ''
    if person.contact==None or person.location==None:
        reply_txt += "Per far funzionare questo servizio abbiamo bisgono di conoscere la tua posizione e avere un tuo recapito telefonico.\n" \
                     "Premi su IMPOSTAZIONI per inserire questi dati o HELP per ottenere maggiori informazioni."
        tell(person.chat_id, reply_txt, kb=[['IMPOSTAZIONI'],['HELP']])
        setState(person, -2)
    else:
        reply_txt += "Premi AVVIA se vuoi cercare o offrire prodotti."
        tell(person.chat_id, reply_txt, kb=[['AVVIA'],['IMPOSTAZIONI'],['HELP']])
        setState(person, -1)

def handleSettings(p,txt=None):
    reply_txt = (txt + '\n') if txt!=None else ''
    if p.contact==None or p.location==None:
        if p.contact==None and p.location==None:
            reply_txt += 'Abbiamo bisogno della tua posizione e di un tuo recapito telefonico'
        elif p.contact==None:
            reply_txt += 'Abbiamo bisogno di un tuo recapito telefonico'
        else:
            reply_txt += 'Abbiamo bisogno della tua posizione'
    else:
        reply_txt += 'Abbiamo già la tua posizione e il tuo contatto ma puoi cambiarle'
    tell(p.chat_id, reply_txt, kb=[['POSIZIONE','RECAPITO'],['TORNA INDIETRO']])
    setState(p, -3)

def setLocation(p, loc):
    p.location =  ndb.GeoPt(loc['latitude'], loc['longitude'])
    p.put()

def setContact(p, contact):
    p.contact =  contact
    p.put()

def init_user(p, cmd, name, last_name, username):
    #if (p.name.decode('utf-8') != name.decode('utf-8')):
    if (p.name != name):
        p.name = name
        p.put()
    #if (p.last_name.decode('utf-8') != last_name.decode('utf-8')):
    if (p.last_name != last_name):
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

def resetNullStatesUsers():
    qry = Person.query()
    count = 0
    for p in qry:
        if (p.state is None): # or p.state>-1
            setState(p,-1)
            count+=1
    return count


def broadcast(msg):
    qry = Person.query().order(-Person.last_mod)
    count = 0
    for p in qry:
        if (p.enabled):
            count += 1
            tell(p.chat_id, "Udite udite..." + ' ' + msg)
            sleep(0.100) # no more than 10 messages per second
    logging.debug('broadcasted to people ' + str(count))

def getInfoCount():
    c = Person.query().count()
    msg = "Attualmente siamo in " + str(c) + " persone iscritte a OpenGarden!" +\
          "Vogliamo crescere assieme!" + "Invita altre persone ad aunirsi!"
    return msg

def tellmyself(p, msg):
    tell(p.chat_id, "Udiete udite... " + msg)

def tell_masters(msg):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg)

def tell_fede(msg):
    for i in range(100):
        tell(key.FEDE_CHAT_ID, "prova " + str(i))
        sleep(0.1)

def tell(chat_id, msg, kb=None, hideKb=True):
    try:
        if kb:
            resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                'chat_id': chat_id,
                'text': msg, #.encode('utf-8'),
                'disable_web_page_preview': 'true',
                #'reply_to_message_id': str(message_id),
                'reply_markup': json.dumps({
                    #'one_time_keyboard': True,
                    'resize_keyboard': True,
                    'keyboard': kb,  # [['Test1','Test2'],['Test3','Test8']]
                    'reply_markup': json.dumps({'hide_keyboard': True})
                }),
            })).read()
        else:
            if hideKb:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg, #.encode('utf-8'),
                    #'disable_web_page_preview': 'true',
                    #'reply_to_message_id': str(message_id),
                    'reply_markup': json.dumps({
                        #'one_time_keyboard': True,
                        'resize_keyboard': True,
                        #'keyboard': kb,  # [['Test1','Test2'],['Test3','Test8']]
                        'reply_markup': json.dumps({'hide_keyboard': True})
                }),
                })).read()
            else:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg, #.encode('utf-8'),
                    #'disable_web_page_preview': 'true',
                    #'reply_to_message_id': str(message_id),
                    'reply_markup': json.dumps({
                        #'one_time_keyboard': True,
                        'resize_keyboard': True,
                        #'keyboard': kb,  # [['Test1','Test2'],['Test3','Test8']]
                        'reply_markup': json.dumps({'hide_keyboard': False})
                }),
                })).read()
        logging.info('send response: ')
        logging.info(resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = Person.query(Person.chat_id==chat_id).get()
            p.enabled = False
            p.put()
            logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))

# ================================
# ================================
# ================================

TOKEN_DURATION_MIN = 100
TOKEN_DURATION_SEC = TOKEN_DURATION_MIN*60

class Token(ndb.Model):
    token_id = ndb.StringProperty()
    start_daytime = ndb.DateTimeProperty()

def createToken():
    now = datetime.now()
    token_id = channel.create_channel(str(now), duration_minutes=TOKEN_DURATION_MIN)
    token = Token.get_or_insert(token_id)
    token.start_daytime = now
    token.token_id = token_id
    token.put()
    return token_id

def updateDashboard():
    #logging.debug('updateDashboard')
    data = {} #getDashboardData()
    qry = Token.query()
    removeKeys = []
    now = datetime.now()
    for t in qry:
        duration_sec = (now - t.start_daytime).seconds
        if (duration_sec>TOKEN_DURATION_SEC):
            removeKeys.append(t.token_id)
        else:
            channel.send_message(t.token_id, json.dumps(data))
    for k in removeKeys:
        ndb.Key(Token, k).delete()

# ================================
# ================================
# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))

class DashboardHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        data = {} #getDashboardData()
        token_id = createToken()
        data['token'] = token_id
        data['today_events'] = json.dumps({}) #getTodayTimeline()
        logging.debug('Requsts: ' + str(data['today_events']))
        template = DASHBOARD_DIR_ENV.get_template('PickMeUp.html')
        logging.debug("Requested Dashboard. Created new token.")
        self.response.write(template.render(data))

class GetTokenHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        token_id = createToken()
        logging.debug("Token handler. Created a new token.")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps({'token': token_id}))

class DashboardConnectedHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        client_id = self.request.get('from')
        logging.debug("Channel connection request from client id: " + client_id)

class DashboardDisconnectedHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        client_id = self.request.get('from')
        logging.debug("Channel disconnection request from client id: " + client_id)

class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(
                json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))

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
        message = body['message']
        #message_id = message.get('message_id')
        # date = message.get('date')
        if "chat" not in message:
            return;
        # fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']
        if "first_name" not in chat:
            return;
        text = message.get('text').encode('utf-8') if "text" in message else ""
        name = chat["first_name"].encode('utf-8')
        last_name = chat["last_name"].encode('utf-8') if "last_name" in chat else "-"
        username = chat["username"] if "username" in chat else "-"
        location = message["location"] if "location" in message else None
        logging.debug('location: ' + str(location))

        def reply(msg=None, kb=None, hideKb=True):
            tell(chat_id, msg, kb, hideKb)

        p = ndb.Key(Person, str(chat_id)).get()

        if p is None:
            # new user
            tell_masters("New user: " + name)
            p = addPerson(chat_id, name)
            logging.info("Text: " + text)
            if text == '/help':
                reply(ISTRUZIONI)
            elif text in ['/start','START']:
                reply("Ciao " + name + ", " + "benvenuto/a!")
                init_user(p, text, name, last_name, username)
                restart(p)
                # state = -1 or -2
            else:
                reply("Qualcosa non ha funzionato... contatta kercos@gmail.com")
        else:
            # known user
            if text=='/state':
              reply("Sei nello stato " + str(p.state) + ": " + STATES[p.state]);
            elif p.state == -1:
                # INITIAL STATE
                if text in ['/help','HELP']:
                    reply(ISTRUZIONI)
                elif text.endswith('AVVIA'):
                    reply('Premi CERCO o OFFRO se vuoi cercare o offrire prodotti', kb = [['CERCO','OFFRO'],[BOTTONE_ANNULLA]])
                    setState(p,0)
                elif text.endswith('IMPOSTAZIONI'):
                    handleSettings(p)
                elif chat_id in key.MASTER_CHAT_ID:
                    if text == '/resetusers':
                        logging.debug('reset user')
                        c = resetNullStatesUsers()
                        reply("Reset states of users: " + str(c))
                    elif text=='/infocount':
                        reply(getInfoCount())
                    elif text == '/resetcounters':
                        resetCounter()
                    elif text == '/test':
                        logging.debug('test')
                        #deferred.defer(tell_fede, "Hello, world!")
                    elif text.startswith('/broadcast ') and len(text)>11:
                        msg = text[11:] #.encode('utf-8')
                        deferred.defer(broadcast, msg)
                    elif text.startswith('/self ') and len(text)>6:
                        msg = text[6:] #.encode('utf-8')
                        tellmyself(p,msg)
                    else:
                        reply('Scusa, capisc solo /help /start '
                              'e altri comandi segreti...')
                    #setLanguage(d.language)
                else:
                    reply("Scusa non capisco quello che hai detto.\n"
                          "Usa i pulsanti sotto o premi HELP per avere informazioni.")
            elif p.state == -2:
                # IMPOSTAZIONI
                if text in ['/help','HELP']:
                    reply(ISTRUZIONI)
                if text.endswith('IMPOSTAZIONI'):
                    handleSettings(p)
            elif p.state == -3:
                # POSIZIONE/CONTATTO
                if text.endswith('TORNA INDIETRO'):
                    restart(p)
                elif text.endswith('POSIZIONE'):
                    setState(p,-4)
                    reply("Usa la graffetta in basso per inviarmi la tua posizione.", kb = [['TORNA INDIETRO']])
                elif text.endswith('RECAPITO'):
                    setState(p,-5)
                    reply("Inserisci le tue informazioni (telefono ed eventualmente un indirizzo email).",
                          kb = [['TORNA INDIETRO']])
            elif p.state == -4:
                # POSIZIONE
                if location!=None:
                    setLocation(p,location)
                    text = 'Grazie per averci inviato la tua posizione!'
                    if p.contact==None:
                        handleSettings(p,txt=text)
                    else:
                        restart(p,txt=text)
                elif text.endswith('TORNA INDIETRO'):
                    handleSettings(p)
                else:
                    reply("Scusa non capisco quello che hai detto.\n"
                          "Ho bisogno di sapere la tua posizione.\n"
                          "Usa la graffetta in basso per inviarmela.", kb = [['TORNA INDIETRO']])
            elif p.state == -5:
                if text.endswith('TORNA INDIETRO'):
                    handleSettings(p)
                elif len(text)==0:
                    reply("Ho bisogno di sapere la tua posizione.\n"
                          "Usa la graffetta in basso per inviarmela.", kb = [['TORNA INDIETRO']])
                else:
                    setContact(p,text)
                    text = 'Grazie per averci inviato il tuo contatto!'
                    if p.location==None:
                        handleSettings(p,txt=text)
                    else:
                        restart(p,txt=text)
                # CONTATTO
            elif p.state == 0:
                # AFTER TYPING START
                if text.endswith("Annulla"):
                    reply("Operazione annullata.")
                    restart(p);
                    # state = -1
                elif text.endswith("CERCO"):
                    setState(p, 20)
                    reply("Bene! Quale prodotti cerchi?", kb=PRODOTTI_ANNULLA)
                elif text.endswith("OFFRO"):
                    setState(p, 30)
                    reply("Bene! Quale prodotti offri?", kb=PRODOTTI_ANNULLA)
                elif text.endswith("Annulla"):
                    reply("Operazione annullata.")
                    restart(p);
                    # state = -1
                else:
                    reply("Scusa non capisco quello che hai detto")
            elif p.state == 20:
                # CERCO PRODOTTI
                if text.endswith("Annulla"):
                    reply("Operazione annullata.")
                    restart(p);
                    # state = -1
                elif text in PRODOTTI_FLAT:
                    table = getListProducts(text, p)
                    if len(table)==0:
                        reply('Nessuna offerta trovata per questo prodotto')
                    else:
                        text = '';
                        for row in table:
                            text += row[0] + ' ' + format_distance(row[1]) + " Contatto: " + row[2] + "\n"
                        reply(text)
                else:
                    reply("Scusa non capisco che prodotto cerchi, ti prego di premere uno dei pulsanti sotto.")
            elif p.state == 30:
                # OFFRO PRODOTTI
                if text.endswith("Annulla"):
                    reply("Operazione annullata.")
                    restart(p);
                    # state = -1
                elif text in PRODOTTI_FLAT:
                    product = getProduct(p.chat_id,text)
                    if (product!=None):
                        reply('Hai già inserito questo prodotto, inseriscine un altro o premi ANNULLA')
                    else:
                        addProduct(p.chat_id, text, p.name, p.location, p.contact)
                        restart(p,txt='Grazie per aver inserito un prodotto!')
                else:
                    reply("Scusa non capisco che prodotto cerchi, ti prego di premere uno dei pulsanti sotto.")
            else:
                reply("Se è verificato un problemino... segnalamelo mandando una mail a kercos@gmail.com")

app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/dashboard', DashboardHandler),
#    ('/_ah/channel/connected/', DashboardConnectedHandler),
#    ('/_ah/channel/disconnected/', DashboardDisconnectedHandler),
    ('/notify_token', GetTokenHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
