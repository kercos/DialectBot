# Run from GAE remote API:
# 	{GAE Path}\remote_api_shell.py -s {YourAPPName}.appspot.com
# 	import export_as_csv

import csv
from google.appengine.ext import ndb
from google.appengine.ext.ndb import metadata
from main import Person, Ride, RideRequest


def exportToCsv(query, csvFileName):
    with open(csvFileName, 'wb') as csvFile:
        csvWriter = csv.writer(csvFile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        #writeHeader(csvWriter)

        first_row = True
        rows = 0

        for e in query:
            #print e
            # Write column labels as first row
            row_dict = e.to_dict()
            if first_row:
                first_row = False
                keys = sorted(row_dict.keys())
                csvWriter.writerow(keys)
            values = []
            v_str = None
            for k in keys:
                v_row = row_dict[k]
                try:
                    v_str = v_row.encode('utf-8') if v_row is str else str(v_row)
                except UnicodeEncodeError:
                    v_str = '--'
                values.append(v_str)
            #print('adding:' + str(values))
            csvWriter.writerow(values)
            rows += 1

        print 'Finished saving ' + str(rows) + ' rows.'


exportToCsv(query = Person.query().order(-Person.last_mod), csvFileName='data/Person_Table.csv')
exportToCsv(query = Ride.query().order(-Ride.start_daytime), csvFileName='data/Ride_Table.csv')
exportToCsv(query = RideRequest.query().order(-RideRequest.passenger_last_seen), csvFileName='data/RideRequest_Table.csv')
