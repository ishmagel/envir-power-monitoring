#!/usr/bin/python
#
# Copyright (C) 2013 DragonHead.

'''Export Envir data to Fusion Tables.'''

import httplib2
import logging
import sqlite3
import sys

#from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run

# Redirect Uri from Simple API Access:
# https://code.google.com/apis/console/b/0/?pli=1#:access
REDIRECT_URI = ''
# Document IDs for Fusion tables:
# https://www.google.com/fusiontables/DataSource?docid=<ID>.
TABLE_IDS = {
    'power': '1dbVgYcR-oMjkI72bNP_JIoO7486xW3CDxZVLEaU',
    'temperature': '1yFM-hTszcGJa2UMLSCSTxiQvHDH1AbOp5L2vUqo'
}
API = 'fusiontables'
VERSION = 'v1'
DATABASE = '/root/app/tonido/plugins/smartnow/data/rt.sqlite3'

class ElectricityFusionClient:
    '''Gathers Envir data from database and exports to Fusion tables.'''

    def __init__(self):
        flow = flow_from_clientsecrets(
            'client_secrets.json',
            scope='https://www.googleapis.com/auth/%s' % API,
            redirect_uri=REDIRECT_URI)

        # This generates the oauth2 file. If run on a server with no access to
        # GUI, it may not be generated. Run on local machine and copy over file.
        storage = Storage('%s-oauth2.json' % sys.argv[0])
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run(flow, storage)

        self.http = httplib2.Http(disable_ssl_certificate_validation=True)
        credentials.authorize(self.http)
        #service = build(API, VERSION, http=self.http)

        self.conn = sqlite3.connect(DATABASE)
 
    def fetch_rows(self, table_name, latest_timestamp=None):
        '''Get rows from Envir database.'''
        query = 'SELECT * FROM %s' % table_name
        if latest_timestamp:
            # Only get new data.
            query = '%s WHERE event_timestamp > "%s"' % (
        	query, latest_timestamp)

        for row in self.conn.execute(query):
            yield row

    def write_to_fusion(self, rows, tableid):
        '''Write data to Fusion table.'''
        body = ''
        for row in rows:
            body += ','.join([str(val or 0) for val in row]) + '\n'

        # Error checking and better reporting in future release.
        # Prints JSON response. Check that rows were received.
        print self.http.request(
          'https://www.googleapis.com/upload/%s/%s/tables/%s/import' % (
              API, VERSION, tableid), 'POST', body=body)

    def write_data(self, datatype):
        '''Get Envir data and write to Fusion tables.'''
        # Read timestamp file to find time to resume from.
        latest_timestamp = None
        try:
            timestamp_file = open('latest_timestamp_%s' % datatype, 'r')
            latest_timestamp = timestamp_file.read()
        except IOError:
            pass

        # Get the rows from the database. 
        rows = list(self.fetch_rows(datatype, latest_timestamp))

        # Find the new latest timestamp.
        for row in rows:
            if not latest_timestamp or latest_timestamp < row[0]:
                latest_timestamp = row[0]

        # Write data to Fusion table.
        self.write_to_fusion(rows, TABLE_IDS[datatype])

        # Write timestamp file with the latest timestamp.
        timestamp_file = open('latest_timestamp_%s' % datatype, 'w')
        timestamp_file.write(latest_timestamp)    

def main():
    '''Run.'''
    logging.basicConfig()
    client = ElectricityFusionClient()
    # Read and export power data.
    client.write_data('power')
    # Read and export temperature data.
    client.write_data('temperature')

if __name__ == '__main__':
    main()
