# -*- coding: utf-8 -*-

import webapp2
from google.appengine.api import urlfetch

import json
import logging
from time import sleep
import key
import person
import recording

import requests

def tell_admin(msg):
    logging.debug(msg)
    for chat_id in key.MASTER_CHAT_ID:
        send_message(chat_id, msg, markdown=False)


# ================================
# Telegram Send Request
# ================================
def sendRequest(chat_id, method, data, files = None, url_api = key.DEFAULT_API_URL, debugInfo=''):
    urlfetch.set_default_fetch_deadline(20)
    try:
        default_timeout = urlfetch.get_default_fetch_deadline()
        logging.info('default_timeout: {}'.format(default_timeout))
        url_api_mathod = url_api + method
        resp = requests.post(url_api_mathod, data=data, files = files)
        logging.info('Response: {}'.format(resp.text))
        respJson = json.loads(resp.text)
        success = respJson['ok']
        if success:
            return True
        else:
            p = person.getPersonByChatId(chat_id)
            status_code = resp.status_code
            error_code = respJson['error_code']
            description = respJson['description']
            if error_code == 403:
                # Disabled user
                p.setEnabled(False, put=True)
                #logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
            elif error_code == 400 and description == "INPUT_USER_DEACTIVATED":
                p.setEnabled(False, put=True)
                debugMessage = '❗ Input user disactivated: ' + p.getFirstNameLastNameUserName()
                logging.debug(debugMessage)
                tell_admin(debugMessage)
            elif error_code == 400 and description == "Bad Request: chat not found":
                p.setEnabled(False, put=True)
                # user never opened a chat with this bot
            else:
                debugMessage = '❗ Raising unknown err ({}).' \
                               '\nStatus code: {}\nerror code: {}\ndescription: {}.'.format(
                    debugInfo, status_code, error_code, description)
                logging.error(debugMessage)
                # logging.debug('recipeint_chat_id: {}'.format(recipient_chat_id))
                logging.debug('Telling to {} who is in state {}'.format(p.chat_id, p.state))
                tell_admin(debugMessage)
    except:
        report_exception()

# ================================
# SEND MESSAGE
# ================================

def send_message(chat_id, msg, kb=None, markdown=True, remove_keyboard=False,
                 inline_keyboard=False, one_time_keyboard=False,
                 sleepDelay=False, hide_keyboard=False, force_reply=False, disable_web_page_preview=True,
                 url_api=key.DEFAULT_API_URL):
    # reply_markup: InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardHide or ForceReply
    if remove_keyboard:
        replyMarkup = {  # InlineKeyboardMarkup
            'remove_keyboard': True
        }
    elif inline_keyboard:
        replyMarkup = {  # InlineKeyboardMarkup
            'inline_keyboard': kb
        }
    elif kb:
        replyMarkup = {  # ReplyKeyboardMarkup
            'keyboard': kb,
            'resize_keyboard': True,
            'one_time_keyboard': one_time_keyboard,
        }
    elif hide_keyboard:
        replyMarkup = {  # ReplyKeyboardHide
            'hide_keyboard': hide_keyboard
        }
    elif force_reply:
        replyMarkup = {  # ForceReply
            'force_reply': force_reply
        }
    else:
        replyMarkup = {}

    data = {
        'chat_id': chat_id,
        'text': msg,
        'disable_web_page_preview': disable_web_page_preview,
        'parse_mode': 'Markdown' if markdown else '',
        'reply_markup': json.dumps(replyMarkup),
    }
    debugInfo = "tell function with msg={} and kb={}".format(msg, kb)
    success = sendRequest(chat_id, method='sendMessage', data=data, debugInfo=debugInfo, url_api=url_api)
    if success:
        if sleepDelay:
            sleep(0.1)
        return True

# ================================
# SEND LOCATION
# ================================

def send_location(chat_id, latitude, longitude, kb=None):
    urlfetch.set_default_fetch_deadline(20)
    data = {
        'chat_id': chat_id,
        'latitude': latitude,
        'longitude': longitude,
    }
    debugInfo = "send_location to chat_id={}".format(chat_id)
    sendRequest(chat_id, method='sendLocation', data=data, debugInfo=debugInfo)

# ================================
# SEND VOICE
# ================================

def send_voice(chat_id, rec):
    urlfetch.set_default_fetch_deadline(20)

    if rec.file_id:
        if rec.date_time < recording.BOT_TRANSITION_DATE:
            rec_data = recording.getRecordingVoiceData(rec.file_id)
            file_data = [('voice', ('voice', rec_data, 'audio/ogg'))]
            data = {
                'chat_id': chat_id,
            }
            debugInfo = "send_voice from old file_id={} to chat_id={}".format(rec.file_id, chat_id)
            sendRequest(chat_id, method='sendVoice', data=data, files=file_data, debugInfo=debugInfo)
        else:
            data = {
                'chat_id': chat_id,
                'voice': rec.file_id,
            }
            debugInfo = "send_voice from new file_id={} to chat_id={}".format(rec.file_id, chat_id)
            sendRequest(chat_id, method='sendVoice', data=data, debugInfo=debugInfo)
    else: # url
        data = {
            'chat_id': chat_id,
            'voice': rec.url,
        }
        debugInfo = "send_voice from url={} to chat_id={}".format(rec.url, chat_id)
        sendRequest(chat_id, method='sendVoice', data=data, debugInfo=debugInfo)


# ================================
# SEND PHOTO
# ================================

def sendPhotoViaUrlOrId(chat_id, url_id, kb=None, sleepDelay=False):
    urlfetch.set_default_fetch_deadline(20)
    if kb:
        replyMarkup = {  # ReplyKeyboardMarkup
            'keyboard': kb,
            'resize_keyboard': True,
        }
    else:
        replyMarkup = {}
    data = {
        'chat_id': chat_id,
        'photo': url_id,
        'reply_markup': json.dumps(replyMarkup),
    }
    debugInfo = "sendPhotoViaUrlOrId with url_id={} to chat_id={}".format(url_id, chat_id)
    success = sendRequest(chat_id, method='sendPhoto', data=data, debugInfo=debugInfo)
    if success:
        if sleepDelay:
            sleep(0.1)
        return True

def sendPhotoFromPngImage(chat_id, img_data, filename='image.png'):
    urlfetch.set_default_fetch_deadline(20)
    img = [('photo', (filename, img_data, 'image/png'))]
    data = {
        'chat_id': chat_id,
    }
    debugInfo = "sendPhotoFromPngImage to chat_id={}".format(chat_id)
    sendRequest(chat_id, method='sendPhoto', data=data, files=img, debugInfo=debugInfo)


# ================================
# SEND DOCUMENT
# ================================

def sendDocument(chat_id, file_id):
    urlfetch.set_default_fetch_deadline(20)
    data = {
        'chat_id': chat_id,
        'document': file_id,
    }
    debugInfo = "sendDocument to chat_id={}".format(chat_id)
    sendRequest(chat_id, method='sendDocument', data=data, debugInfo=debugInfo)

'''
def sendExcelDocument(chat_id, sheet_tables, filename='file'):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    import utility
    try:
        xlsData = utility.convert_data_to_spreadsheet(sheet_tables)
        files = [('document', ('{}.xls'.format(filename), xlsData, 'application/vnd.ms-excel'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.TELEGRAM_API_URL + 'sendDocument', data=data, files=files)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()
'''

# ================================
# SEND WAITING ACTION
# ================================

def sendWaitingAction(chat_id, action_tipo='typing', sleep_time=None):
    urlfetch.set_default_fetch_deadline(20)
    data = {
        'chat_id': chat_id,
        'action': action_tipo,
    }
    debugInfo = "sendWaitingAction to chat_id={}".format(chat_id)
    sendRequest(chat_id, method='sendChatAction', data=data, debugInfo=debugInfo)
    if sleep_time:
        sleep(sleep_time)

# ================================
# HANDLERS
# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(20)
        botname = self.request.get('botname').lower()
        api_url = key.DIALECT_API_URL if botname == 'dialectbot' else key.DIALETTI_API_URL
        json_response = requests.get(api_url + 'getMe').json()
        self.response.write(json.dumps(json_response))
        # self.response.write(json.dumps(json.load(urllib2.urlopen(key.TELEGRAM_API_URL + 'getMe'))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(20)
        botname = self.request.get('botname').lower()
        api_url = key.DIALECT_API_URL if botname == 'dialectbot' else key.DIALETTI_API_URL
        webhook_url = key.DIALECT_WEBHOOK_URL if botname == 'dialectbot' else key.DIALETTI_WEBHOOK_URL
        allowed_updates = ["message", "edited_message", "inline_query", "chosen_inline_result", "callback_query"]
        data = {
            'url': webhook_url,
            'allowed_updates': json.dumps(allowed_updates),
        }
        resp = requests.post(api_url + 'setWebhook', data)
        logging.info('SetWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

class GetWebhookInfo(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(20)
        botname = self.request.get('botname').lower()
        api_url = key.DIALECT_API_URL if botname == 'dialectbot' else key.DIALETTI_API_URL
        resp = requests.post(api_url + 'getWebhookInfo')
        logging.info('GetWebhookInfo Response: {}'.format(resp.text))
        self.response.write(resp.text)

class DeleteWebhook(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(20)
        botname = self.request.get('botname').lower()
        api_url = key.DIALECT_API_URL if botname == 'dialectbot' else key.DIALETTI_API_URL
        resp = requests.post(api_url + 'deleteWebhook')
        logging.info('DeleteWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

def report_exception():
    import traceback
    msg = "❗ Detected Exception: " + traceback.format_exc()
    tell_admin(msg)
    logging.error(msg)
