#!/usr/bin/python

import time
from geopy.geocoders import Nominatim


geolocator = Nominatim()

def getGPS(place):
    #location = geolocator.geocode("Acquafredda di Maratea, Italia")
    location = geolocator.geocode(place)
    if not location:
        return 'NOT FOUND'
    #print(str(place).encode("utf-8"))
    #print(str(location).encode("utf-8"))
    return '(' + str(location.latitude) + ', ' + str(location.longitude) + ')'


inputCityFile = open("/Users/fedja/Work/Code/JavaCode/DialectCrawler/data/cities.tsv")
outptputCityFileGPS = open("/Users/fedja/Work/Code/JavaCode/DialectCrawler/data/citiesGPS.tsv", "w")

for line in inputCityFile:
    city = line.strip()
    location = city + ", Italia"
    gps = getGPS(location)
    outputLine = city + "\t" + gps
    print(outputLine)
    #print(line)
    outptputCityFileGPS.write(outputLine + '\n')
    time.sleep( 0.1 )

inputCityFile.close()
outptputCityFileGPS.close()