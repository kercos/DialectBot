
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import urllib, urllib2
import webapp2
import logging
import random
import json
import os

from geo import geomodel, geotypes
import key
import person
import time_util
import sys
import utility

REC_APPROVED_STATE_IN_PROGRESS = 'IN PROGRESS' #being filled in
REC_APPROVED_STATE_TRUE = 'TRUE' #submitted
REC_APPROVED_STATE_FALSE = 'FALSE' #submitted and closed

class Recording(geomodel.GeoModel, ndb.Model):
    # location = ndb.GeoPtProperty() # inherited from geomodel.GeoModel
    chat_id = ndb.IntegerProperty()
    date_time = ndb.DateTimeProperty()
    file_id = ndb.StringProperty()
    url = ndb.StringProperty()
    random_id = ndb.FloatProperty()
    translation = ndb.StringProperty()
    approved = ndb.StringProperty(default=REC_APPROVED_STATE_IN_PROGRESS)

    def approve(self, value):
        self.approved = value
        self.put()

    def getRecCommand(self, escape=True):
        result = "/rec_{}".format(self.key.id())
        if escape:
            result = utility.escapeMarkdown(result)
        return result

def addRecording(person, file_id):
    #approxLocs = getApproxLocations(person.location.lat,person.location.lon)
    r = Recording()
    r.populate(chat_id=person.chat_id, location = person.location,
               date_time=time_util.now(), file_id=file_id, random_id = random.random())
    r.put()
    return r

def deleteRecording(file_id):
    rec = getRecording(file_id)
    rec.key.delete()

def getRecordingCheckIfUrl(file_id_or_url):
    if (file_id_or_url.startswith("http")):
        rec = Recording.query(Recording.url == file_id_or_url).get()
    else:
        rec = Recording.query(Recording.file_id == file_id_or_url).get()
    return rec

def getRecording(file_id):
    rec = Recording.query(Recording.file_id == file_id).get()
    return rec

def addTranslation(file_id, translation):
    rec = getRecording(file_id)
    rec.translation = translation
    rec.put()

def getRandomRecording():
    r = random.random()
    random_entry = Recording.query(
        Recording.approved == REC_APPROVED_STATE_TRUE,
        Recording.random_id>r,
        #Recording.file_id!=None
    ).order(Recording.random_id).get()
    if not random_entry:
        random_entry = Recording.query(
            Recording.approved == REC_APPROVED_STATE_TRUE,
            Recording.random_id<r,
            #Recording.file_id != None
        ).order(-Recording.random_id).get()
    if random_entry:
        logging.debug("Random number: " + str(r) + " Selected random id: " + str(random_entry.random_id))
    return random_entry

def getClosestRecording(lat, lon, search_radius, random_radius):
    import geoUtils

    qry = Recording.query(Recording.approved == REC_APPROVED_STATE_TRUE)
    latMin, lonMin, latMax, lonMax = geoUtils.getBoxCoordinates(lat, lon, search_radius)
    logging.debug("Lat={}, Lon={}, radius={}, latMin={}, lonMin={}, latMax={}, lonMax={}".format(
        lat, lon, search_radius, latMin, lonMin, latMax, lonMax))
    box = geotypes.Box(latMax, lonMax, latMin, lonMin)  # north, east, south, west

    recs = Recording.bounding_box_fetch(qry, box)
    num_results = len(recs)

    if num_results==0:
        return None
    if num_results==1:
        return recs[0]
    else:
        minDstRecs = []
        minDst = sys.maxint
        for r in qry:
            dst = geoUtils.distance((lat,lon),(r.location.lat, r.location.lon))
            if dst<(minDst-random_radius):
                minDst = dst
                minDstRecs = [r]
            elif dst<(minDst+random_radius):
                minDstRecs.append(r)
        size = len(minDstRecs)
        randomIndx = int(size*random.random())
        return minDstRecs[randomIndx]

def testVivaldi():
    file = open("vivaldi/citiesGPS.tsv")
    count = 0
    for line in file:
        count += 1
    logging.debug('number of lines: ' + str(count))

def removeFormatVoice():
    qry = Recording.query()
    count = 0
    for rec in qry:
        if 'format_voice' in rec._properties:
            del rec._properties['format_voice']
            rec.put()
            count+=1
    return count

def deleteVivaldi():
    ndb.delete_multi(
        Recording.query(Recording.chat_id==0).fetch(keys_only=True)
    )

def countVivaldi():
    return Recording.query(Recording.chat_id==0).count()

def importVivaldi():
    vivaldiBaseUrl = "https://dl.dropboxusercontent.com/u/12016006/Vivaldi/ogg/"
    cityFile = open("vivaldi/citiesGPS.tsv")
    #recFile = open("vivaldi/recStructure_3_4.tsv")
    recFile = open("vivaldi/sample_10_feb_16.tsv")
    cityDictionary = {}
    count = 0
    for line in cityFile:
        city_gps = line.split("\t")
        city = city_gps[0]
        #logging.debug("'" + city_gps[1] + "'")
        loc_string = city_gps[1] #(45.6051865, 10.6900516)
        loctext_split = loc_string[1:-2].split(", ") #trim the \n
        loc = {'latitude': float(loctext_split[0]), 'longitude': float(loctext_split[1])}
        cityDictionary[city] = loc
    listOfRecEntities = []
    for line in recFile:
        # region|translation|city|file
        rtcf = line.split("\t")
        translation = rtcf[1] + " (credits to Vivaldi project, see https://www2.hu-berlin.de/vivaldi)"
        city = rtcf[2]
        locGps =  cityDictionary[city]
        locGeoPt =  ndb.GeoPt(locGps['latitude'], locGps['longitude'])
        fileName = rtcf[3][:-1] #trim the \n
        url = vivaldiBaseUrl + fileName
        r = Recording()
        r.populate(chat_id=0, location = locGeoPt,
               date_time=time_util.now(), url=url, random_id = random.random(), translation = translation)
        listOfRecEntities.append(r)
        count += 1
        if (count==50):
            ndb.put_multi(listOfRecEntities)
            listOfRecEntities = []
            count = 0
    ndb.put_multi(listOfRecEntities)


def setAllRecApproved():
    listOfRecEntities = []
    count = 0
    for rec in Recording.query():
        rec.approved = REC_APPROVED_STATE_TRUE
        listOfRecEntities.append(rec)
        count += 1
        if count % 10 == 0:
            print count
    ndb.put_multi(listOfRecEntities)

def getInfoApproved():
    totalCount = Recording.query().count()
    totalApproved = Recording.query(Recording.approved == REC_APPROVED_STATE_TRUE).count()
    print "Total count: " + str(totalCount)
    print "Approved: " + str(totalApproved)

###########################
## RECORDINGS MAP
###########################

# Run from GAE remote API:
# 	{GAE Path}\remote_api_shell.py -s dialectbot.appspot.com
# 	import export_as_csv

class DownloadRecordingHandler(webapp2.RequestHandler):
    def get(self, file_id):
        if file_id.endswith('.oga'):
            file_id = file_id[:-4]
        urlfetch.set_default_fetch_deadline(60)
        logging.debug("Requested file_id: " + file_id)
        rec = getRecording(file_id)
        if rec:
            resp = urllib2.urlopen(key.BASE_URL + 'getFile', urllib.urlencode(
                {'file_id': rec.file_id})).read()
            file_path = json.loads(resp)['result']['file_path']
            urlFile = key.BASE_URL_FILE + file_path
            logging.debug("Url file: " + urlFile)
            voiceFile = urllib.urlopen(urlFile).read()

            self.response.headers['Content-Type'] = 'application/octet-stream'
            self.response.headers['Content-Disposition'] = 'filename="%s.oga"' % (file_id)
            self.response.out.write(voiceFile)
        else:
            logging.debug("Rec not found")
            self.response.write('No recording found')
            self.response.set_status(404)

        #url = self.request.get() #'url'
        #if file_id:
        #    self.response.write(file_id)
        #json.dumps(json.load(urllib2.urlopen(key.BASE_URL + 'setWebhook', urllib.urlencode({'url': url}))))


class ServeDynamicAudioGeoJsonFileHandler(webapp2.RequestHandler):
    def get(self):
        geoJsonStructure = getAudioGeoJsonStructure()
        self.response.write(json.dumps(geoJsonStructure, indent=4))

ADD_RANDOM_NOISE_TO_COORDINATES = True
MAX_COORDINATES_RANDOM_NOISE = 0.01 #about 1 Km

def createGeoJsonElement(rec, addRandomCoordNoise=True):
    longitude = rec.location.lon
    latitude = rec.location.lat
    if addRandomCoordNoise:
        longitude += utility.getRandomFloat(MAX_COORDINATES_RANDOM_NOISE)
        latitude += utility.getRandomFloat(MAX_COORDINATES_RANDOM_NOISE)
    name_text = person.getPersonByChatId(rec.chat_id).getFirstName()
    translation_text = rec.translation.encode('utf-8') if rec.translation else "(nessuna traduzione)"
    audioUrl = "http://dialectbot.appspot.com/recordings/{0}.oga".format(rec.file_id)
    element = {
        "type": "Feature",
        "properties": {
            "person": name_text,
            "translation": translation_text,
            # "place"
            "date": rec.date_time.strftime("%d-%m-%Y"),
            "audio": "<p><audio width='300' height='32' src='{0}' "
                     "controls='controls' preload='none' type='audio/ogg; codecs=vorbis'><br />"
                     "Your browser does not support the audio element.<br /></audio></p>".format(audioUrl)
        },
        "geometry": {
            "type": "Point",
            "coordinates": [longitude, latitude]
        }
    }
    return element

def createAudioGeoJsonStructure():
    structure = []
    qry = Recording.query(Recording.file_id != None, Recording.approved == REC_APPROVED_STATE_TRUE)
    for rec in qry:
        element = createGeoJsonElement(rec, addRandomCoordNoise=ADD_RANDOM_NOISE_TO_COORDINATES)
        structure.append(element)
    return structure

RECORDING_MANAGER_ID = "RECORDING_MANAGER"

class RecordingManager(ndb.Model):
    geoJsonStructure = ndb.PickleProperty()

def initializeGeoJsonStructure():
    recManagerEntry = RecordingManager.get_or_insert(RECORDING_MANAGER_ID)
    recManagerEntry.geoJsonStructure = createAudioGeoJsonStructure()
    recManagerEntry.put()

def appendRecordingInGeoJsonStructure(rec):
    recManagerEntry = RecordingManager.get_or_insert(RECORDING_MANAGER_ID)
    element = createGeoJsonElement(rec, ADD_RANDOM_NOISE_TO_COORDINATES)
    recManagerEntry.geoJsonStructure.append(element)
    recManagerEntry.put()

def getAudioGeoJsonStructure():
    recManagerEntry = RecordingManager.get_by_id(RECORDING_MANAGER_ID)
    structure = recManagerEntry.geoJsonStructure
    return {
        "type": "FeatureCollection",
        "features": structure
    }

def getRecordingCounts(onlyCrowdsourced = True):
    if onlyCrowdsourced:
        return Recording.query(Recording.url == None).count()
    else:
        return Recording.query().count()

def getRecordingNames():
    recs =  Recording.query(Recording.url == None).fetch()
    chat_id_set = set([r.chat_id for r in recs])
    names = []
    for id in chat_id_set:
        p = person.getPersonByChatId(id)
        names.append(p.getFirstName())
    return ', '.join(names)

def updateAllRecordings():
    recs = Recording.query().fetch()
    for r in recs:
        #r.update_location()
        for prop in ['location_approx_det_0', 'location_approx_det_1', 'location_approx_det_2', 'location_approx_det_3', 'location_approx_det_4']:
            if prop in r._properties:
                del r._properties[prop]
    create_futures = ndb.put_multi_async(recs)
    ndb.Future.wait_all(create_futures)

def updateVivaldi():
    recs  = Recording.query(Recording.chat_id==0).fetch()
    for r in recs:
        r.url = r.url.replace('.OGG','.ogg')
    create_futures = ndb.put_multi_async(recs)
    ndb.Future.wait_all(create_futures)
