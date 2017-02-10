from geopy.geocoders import Nominatim
from geopy.geocoders import GoogleV3
from geopy.distance import vincenty
from geopy.exc import GeocoderTimedOut
from geopy.exc import GeocoderServiceError
import math
import key
import logging
import requests
import jsonUtil
from geoLocation import GeoLocation

#https://raw.githubusercontent.com/dakk/Italia.json/master/italia_comuni.json

GEOLOCATOR_1 = Nominatim()
GEOLOCATOR_2 = GoogleV3(key.GOOGLE_API_KEY)

def getLocationFromName(locationName):
    try:
        for g in [GEOLOCATOR_1, GEOLOCATOR_2]:
            location = g.geocode(
                #locationName, timeout=10, exactly_one=True, language='it', region='it') #default one answer for Nominatim (not google)
                locationName, timeout=10, exactly_one=True, language='it')  # default one answer for Nominatim (not google)
            if location :
                return location
    except GeocoderServiceError:
        logging.error('GeocoderServiceError occurred')

'''
def getLocationFromPosition(lat, lon):
    try:
        for g in [GEOLOCATOR_1, GEOLOCATOR_2]:
            location = g.reverse((lat, lon), timeout=10, exactly_one=True, language='it')  # default one answer for Nominatim (not google)
            if location :
                return location
    except GeocoderServiceError:
        logging.error('GeocoderServiceError occurred')
'''

def getBoxCoordinates(lat, lon, radius):
    loc = GeoLocation.from_degrees(lat, lon)
    boxMinMaxCorners = loc.bounding_locations(radius)
    boxMinCorners = boxMinMaxCorners[0]
    boxMaxCorners = boxMinMaxCorners[1]
    latMin = boxMinCorners.deg_lat
    lonMin = boxMinCorners.deg_lon
    latMax = boxMaxCorners.deg_lat
    lonMax = boxMaxCorners.deg_lon
    return latMin, lonMin, latMax, lonMax

# see https://developers.google.com/maps/documentation/geocoding/intro
# e.g., http://maps.googleapis.com/maps/api/geocode/json?language=it&region=it&latlng=46.0682115,11.1221167665254
# e.g., https://maps.googleapis.com/maps/api/geocode/json?language=it&region=it&location_type=ROOFTOP&result_type=street_address&latlng=46.069141,11.152745&key=AIzaSyCjmN2mmOviJXuJishwacbc-q4FQwYiFro
# e.g., https://maps.googleapis.com/maps/api/geocode/json?language=it&region=it&location_type=ROOFTOP&result_type=street_address&address=via del roro, 6A, 38052, Caldonazzo, TN&key=AIzaSyCjmN2mmOviJXuJishwacbc-q4FQwYiFro
googleapis_url = "https://maps.googleapis.com/maps/api/geocode/json?"

def getComuneProvinciaFromCoordinates(lat, lon):
    params = {
        'language': 'it',
        'latlng': '{},{}'.format(lat,lon),
        'key': key.GOOGLE_API_KEY
    }
    resp = requests.get(googleapis_url, params=params)
    #logging.info('Response: {}'.format(resp.text)) #this might generate a UnicodeEncodeError: 'ascii' codec can't encode character u'\xe0' in position 607: ordinal not in range(128)
    responseJson = jsonUtil.json_loads_byteified(resp.text)
    if responseJson['status']=='OK':
        results = responseJson['results']
        for result_item in results:
            address_components = result_item['address_components']
            comune_field = [x for x in address_components if x['types']==[ "administrative_area_level_3", "political" ]]
            comune = comune_field[0]["long_name"] if comune_field else None
            provincia_field = [x for x in address_components if x['types']==[ "administrative_area_level_2", "political" ]]
            provincia = provincia_field[0]["long_name"] if provincia_field else None
            if comune and provincia:
                return "{}, {}".format(comune, provincia)
        #return provincia
    #raise LookupError('Problem finding comune and provincia from coordinates {} {}'.format(lat, lon))
    logging.debug("No comune found for {} {}".format(lat, lon))
    return None


def distance(point1, point2):
    #point1 = (41.49008, -71.312796)
    #point2 = (41.499498, -81.695391)
    return vincenty(point1, point2).kilometers


def getLocationTest():
    #location = GEOLOCATOR.geocode("175 5th Avenue NYC") #default one answer for Nominatim (not google)
    #location = GEOLOCATOR.geocode("via garibaldi", exactly_one=False)
    location = GEOLOCATOR_1.reverse("52.509669, 13.376294", exactly_one=True, language='it')
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
