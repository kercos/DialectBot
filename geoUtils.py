from geopy.geocoders import Nominatim
from geopy.geocoders import GoogleV3
from geopy.distance import vincenty
from geopy.exc import GeocoderTimedOut
from geopy.exc import GeocoderServiceError
import math
import key
import googlemaps
import logging
import urllib
import jsonUtil

#https://raw.githubusercontent.com/dakk/Italia.json/master/italia_comuni.json

GEOLOCATOR = Nominatim()
#GEOLOCATOR = GoogleV3(key.GOOGLE_API_KEY)

def getLocationFromName(locationName):
    try:
        #location = GEOLOCATOR.geocode(locationName, timeout=10, exactly_one=True, language='it', region='it') #default one answer for Nominatim (not google)
        location = GEOLOCATOR.geocode(locationName, timeout=10, exactly_one=True, language='it')  # default one answer for Nominatim (not google)
        return location
    except GeocoderServiceError:
        logging.error('GeocoderServiceError occored')


def getAddressFromPosition(lat, lon):
    try:
        location = GEOLOCATOR.reverse((lat, lon), timeout=10, exactly_one=True, language='it') #default one answer for Nominatim (not google)
        return location.address.encode('utf-8')
    except GeocoderServiceError:
        logging.error('GeocoderServiceError occored')

# see http://maps.googleapis.com/maps/api/geocode/json?language=it&latlng=46.0682115,11.1221167665254&sensor=true
def getComuneProvinciaFromCoordinates(lat, lon):
    url = "https://maps.googleapis.com/maps/api/geocode/json?" \
          "language=it&latlng={},{}&sensor=true&key={}".format(lat,lon,key.GOOGLE_API_KEY)
    #logging.debug(url)
    response = urllib.urlopen(url)
    emojiTagsDict = jsonUtil.json_loads_byteified(response.read())
    #logging.debug(str(emojiTagsDict))
    if emojiTagsDict['status']=='OK':
        results = emojiTagsDict['results']
        address_components = results[0]['address_components']
        comune = [x for x in address_components if x['types']==[ "administrative_area_level_3", "political" ]][0]["long_name"]
        provincia = [x for x in address_components if x['types']==[ "administrative_area_level_2", "political" ]][0]["long_name"]
        return "{}, {}".format(comune, provincia)
    return None

def distance(point1, point2):
    #point1 = (41.49008, -71.312796)
    #point2 = (41.499498, -81.695391)
    return vincenty(point1, point2).kilometers


def getLocationTest():
    #location = GEOLOCATOR.geocode("175 5th Avenue NYC") #default one answer for Nominatim (not google)
    #location = GEOLOCATOR.geocode("via garibaldi", exactly_one=False)
    location = GEOLOCATOR.reverse("52.509669, 13.376294", exactly_one=True, language='it')
    #address = location.address
    return location

def getLocationTest1():
    newport_ri = (41.49008, -71.312796)
    cleveland_oh = (41.499498, -81.695391)
    return vincenty(newport_ri, cleveland_oh).kilometers


# ================================
# ================================
# ================================


#gmaps = googlemaps.Client(key=key.GOOGLE_API_KEY)

# def test_Google_Map_Api():
#     # Geocoding an address
#     geocode_result = gmaps.geocode('bari')
#     logging.debug("gmaps geocode result: " + str(geocode_result))
#     return geocode_result

    # Look up an address with reverse geocoding
    #reverse_geocode_result = gmaps.reverse_geocode((40.714224, -73.961452))

GOOGLE_LOCATOR = GoogleV3(key.GOOGLE_API_KEY)

def test_Google_Map_Api():
    geocode_result = GOOGLE_LOCATOR.geocode('bari', exactly_one=True)
    logging.debug("gmaps geocode result: " + str(geocode_result))
    return geocode_result

# ================================
# ================================
# ================================

EARTH_RADIUS = 6371 #Earth's Radius in Kms.

def HaversineDistance(lat1, lon1, lat2, lon2):
    """Method to calculate Distance between two sets of Lat/Lon."""

    #Calculate Distance based in Haversine Formula
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = EARTH_RADIUS * c
    return d
