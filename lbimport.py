#!/usr/bin/env python

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

'''
Import your loved and banned tracks to a gnu fm server.
Usage: lbimport.py --user=Username --type=loved --file=mylovedtracks.txt [--server=SERVER]

'''

import json, sys, os, urllib, urllib2, hashlib, getpass, time
from optparse import OptionParser

def get_options(parser):
    """ Define command line options."""
    parser.add_option("-u", "--user", dest="username", default=None,
                      help="User name.")
    parser.add_option("-f", "--file", dest="infile", default=None,
                      help="File with tracks to read from.")
    parser.add_option("-s", "--server", dest="server", default="libre.fm",
                      help="Server to send tracks to, default is libre.fm")
    parser.add_option("-t", "--type", dest="infotype", default=None,
                      help="Type of tracks you are about to import, loved or banned.")
    options, args = parser.parse_args()

    if not options.username:
        sys.exit('User name not specified, see --help')

    if not options.infotype in ['loved', 'unloved', 'banned', 'unbanned']:
        sys.exit('No or invalid type of track specified, see --help')

    if not options.infile:
        sys.exit('File with tracks not specified, see --help')

    if options.server == 'libre.fm':
        options.server = 'http://alpha.libre.fm'
    else:
        if options.server[:7] != 'http://':
            options.server = 'http://%s' % options.server
          
    return options.server, options.username, options.infile, options.infotype

def auth(fmserver, user, password):
    passmd5 = hashlib.md5(password).hexdigest()
    token = hashlib.md5(user+passmd5).hexdigest()
    getdata = dict(method='auth.getMobileSession', username=user, authToken=token, format='json')
    req = fmserver + '/2.0/?' + urllib.urlencode(getdata)
    response = urllib2.urlopen(req)
    try:
        jsonresponse = json.load(response)
        sessionkey = jsonresponse['session']['key']
    except:
        print jsonresponse
        sys.exit(1)

    return sessionkey

def submit(fmserver, infotype, trackartist, tracktitle, sessionkey):

    if infotype == 'loved':
        libremethod = 'track.love'
    elif infotype == 'unloved':
        libremethod = 'track.unlove'
    elif infotype == 'banned':
        libremethod = 'track.ban'
    elif infotype == 'unbanned':
        libremethod = 'track.unban'
    else:
        sys.exit('invalid method')

    postdata = dict(method=libremethod, artist=trackartist, track=tracktitle, sk=sessionkey, format='json')
    req = urllib2.Request(fmserver + '/2.0/', urllib.urlencode(postdata))
    response = urllib2.urlopen(req)
    
    try:
        jsonresponse = json.load(response)
        status = jsonresponse['lfm']['status']

        if status == "ok":
            return True
    except:
        return False

def main(server, username, infile, infotype):
    password = getpass.getpass()
    sessionkey = auth(server, username, password)

    n = 0
    for line in file(infile):
        n += 1
        timestamp, track, artist, album, trackmbid, artistmbid, albummbid = line.strip("\n").split("\t")
        if submit(server, infotype, artist, track, sessionkey):
            print "%d: %s %s - %s" % (n, infotype, artist, track)
        else:
            print "FAILED: %s - %s" % (artist, track)
        time.sleep(0.5)
 
if __name__ == '__main__':
    parser = OptionParser()
    server, username, infile, infotype = get_options(parser)
    main(server, username, infile, infotype)
