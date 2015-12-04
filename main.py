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
#from flask import Flask, jsonify

import gettext

from jinja2 import Environment, FileSystemLoader

# ================================
# ================================
# ================================

BASE_URL = 'https://api.telegram.org/bot' + key.TOKEN + '/'

DASHBOARD_DIR_ENV = Environment(loader=FileSystemLoader('dashboard'), autoescape = True)
tell_completed = False

STATES = {

}


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


class Person(ndb.Model):
    name = ndb.StringProperty()
    last_name = ndb.StringProperty(default='-')
    username = ndb.StringProperty(default='-')
    last_mod = ndb.DateTimeProperty(auto_now=True)
    last_seen = ndb.DateTimeProperty()
    chat_id = ndb.IntegerProperty()
    state = ndb.IntegerProperty(default=-1)
    last_type = ndb.StringProperty(default='-1')
    location = ndb.GeoPtProperty()
    enabled = ndb.BooleanProperty(default=True)


def addPerson(chat_id, name):
    p = Person.get_or_insert(str(chat_id))
    p.name = name
    p.chat_id = chat_id
    p.put()
    return p

def setType(p, type):
    p.last_type = type
    p.put()

def setState(p, state):
    p.state = state
    p.put()

def restart(person):
    tell(person.chat_id, "Premi START se vuoi ricominciare", kb=[['START','HELP']])
    setState(person, -1)

def setLocation(p, loc):
    p.location = loc
    p.put()

def start(p, cmd, name, last_name, username):
    #logging.debug(p.name + _(' ') + cmd + _(' ') + str(p.enabled))
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
        if cmd=='/start':
            p.enabled = True
            p.put()
        else: # START when diasbled
            return
    tell(p.chat_id, "Ciao " + p.name.encode('utf-8') + '! ' + "Cerchi o offri qualcosa?"),
    kb=[["Cerco", "Offro"],[emoij.NOENTRY + " Annulla"]]
    setState(p,0)

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
    msg = _("We are now") + _(' ') + str(c) + _(' ') + _("people subscribed to OpenGarden!") + _(' ') +\
          _("We want to get bigger and bigger!") + _(' ') + _("Invite more people to join us!")
    return msg

def tellmyself(p, msg):
    tell(p.chat_id, "Listen listen... " + msg)

def updateLastSeen(p):
    p.last_seen = datetime.now()
    p.put()

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
            logging.info('Disabled user: ' + p.name.encode('utf-8') + _(' ') + str(chat_id))

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
        message_id = message.get('message_id')
        # date = message.get('date')
        if "text" not in message:
            return;
        text = message.get('text').encode('utf-8')
        # fr = message.get('from')
        if "chat" not in message:
            return;
        chat = message['chat']
        chat_id = chat['id']
        if "first_name" not in chat:
            return;
        name = chat["first_name"].encode('utf-8')
        last_name = chat["last_name"].encode('utf-8') if "last_name" in chat else "-"
        username = chat["username"] if "username" in chat else "-"

        def reply(msg=None, kb=None, hideKb=True):
            tell(chat_id, msg, kb, hideKb)

        p = ndb.Key(Person, str(chat_id)).get()


        instructions =  "OpenGarden Instructions"

        disclaimer = "OpenGarden Disclaimer"

        if p is None:
            # new user
            tell_masters("New user: " + name)
            p = addPerson(chat_id, name)
            if text == '/help':
                reply(instructions)
            elif text in ['/start','START']:
                start(p, text, name, last_name, username)
                # state = 0
            else:
                reply(_("Hi") + _(' ') + name + ", " + _("welcome!"))
                reply(instructions)
        else:
            # known user
            if text=='/state':
              reply("You are in state " + str(p.state) + ": " + STATES[p.state]);
            elif p.state == -1:
                # INITIAL STATE
                if text in ['/help','HELP']:
                    reply(instructions)
                elif text == _('DISCLAIMER'):
                    reply(disclaimer)
                elif text in ['/start','START']:
                    start(p, text, name, last_name, username)
                    # state = 0
                elif text == _('SETTINGS'):
                    reply(_("Settings options"),
                          kb=[[_('LANGUAGE')], [_('INFO USERS'),_('DAY SUMMARY')],[emoij.NOENTRY + _(' ') + _("Abort")]])
                    setState(p, 90)
                elif chat_id in key.MASTER_CHAT_ID:
                    if text == '/resetusers':
                        logging.debug('reset user')
                        c = resetNullStatesUsers()
                        reply("Reset states of users: " + str(c))
                        #restartAllUsers('Less spam, new interface :)')
                        #resetLastNames()
                        #resetEnabled()
                        #resetLanguages()
                        #resesetNames()
                    elif text=='/infocount':
                        reply(getInfoCount())
                    elif text == '/resetcounters':
                        resetCounter()
                    elif text == '/test':
                        logging.debug('test')
                        #tell_katja_test()
                        #updateDashboard()
                        #reply('test')
                        #reply(getInfoDay())
                        #tell_masters('test')
                        #reply(getInfoWeek())
                        #testQueue()
                        #msg = "Prova di broadcasting.\n" + \
                        #      "Se lo ricevi una sola volta vuol dire che da ora in poi funziona :D (se no cerchiamo di risolverlo)\n\n" + \
                        #      "Broadcasting test.\n" + \
                        #      "If you receive it only once it means that now it works correctly :D (if not we will try to fix it)"
                        #msg = "Last  broadcast test for today :P"
                        #broadcastQueue(msg)
                        deferred.defer(tell_fede, "Hello, world!")
                    elif text.startswith('/broadcast ') and len(text)>11:
                        msg = text[11:] #.encode('utf-8')
                        deferred.defer(broadcast, msg)
                    elif text.startswith('/self ') and len(text)>6:
                        msg = text[6:] #.encode('utf-8')
                        tellmyself(p,msg)
                    else:
                        reply('Sorry, I only understand /help /start'
                              '/users and other secret commands...')
                    #setLanguage(d.language)
                else:
                    reply(_("Sorry, I don't understand you"))
                    restart(p)
            #kb=[[emoij.CAR + _(' ') + _("Driver"), emoij.FOOTPRINTS + _(' ') + _("Passenger")],[emoij.NOENTRY + _(' ') + _("Abort")]])
            elif p.state == 0:
                # AFTER TYPING START
                #logging.debug(text, type(text))
                if text.endswith(_("Cerco")):
                #if text == emoij.FOOTPRINTS + _(' ') + _("Passenger"):
                    setState(p, 20)
                    setType(p, text)
                elif text.endswith(_("Offro")):
                #elif text == emoij.CAR + _(' ') + _("Driver"):
                    setState(p, 30)
                    setType(p, text)
                elif text.endswith(_("Abort")):
                #elif text == emoij.NOENTRY + _(' ') + _("Abort"):
                    reply(_("Passage aborted."))
                    restart(p);
                    # state = -1
                else: reply(_("Sorry, I don't understand you"))
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
