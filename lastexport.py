#!/usr/bin/env python
#-*- coding: utf-8 -*-

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

"""
Script for exporting tracks through audioscrobbler API.
Usage: lastexport.py -u USER [-o OUTFILE] [-p STARTPAGE] [-s SERVER]
"""

import urllib2, urllib, sys, time, re
from xml.dom import minidom
from optparse import OptionParser

def get_options(parser):
    """ Define command line options."""
    parser.add_option("-u", "--user", dest="username", default=None,
                      help="User name.")
    parser.add_option("-o", "--outfile", dest="outfile", default="exported_tracks.txt",
                      help="Output file, default is exported_tracks.txt")
    parser.add_option("-p", "--page", dest="startpage", type="int", default="1",
                      help="Page to start fetching tracks from, default is 1")
    parser.add_option("-s", "--server", dest="server", default="last.fm",
                      help="Server to fetch track info from, default is last.fm")
    options, args = parser.parse_args()

    if not options.username:
        sys.exit("User name not specified, see --help")
         
    return options.username, options.outfile, options.startpage, options.server

def connect_server(username, startpage):
    """ Connect to server and get a XML page."""
    if server == "libre.fm":
        baseurl = 'http://alpha.libre.fm/2.0/?'
        urlvars = dict(method='user.getrecenttracks',
                    api_key='ohaiderthisisthelastexportscript',
                    user=username,
                    page=startpage,
                    limit=200)

    elif server == "last.fm":
        baseurl = 'http://ws.audioscrobbler.com/2.0/?'
        urlvars = dict(method='user.getrecenttracks',
                    api_key='e38cc7822bd7476fe4083e36ee69748e',
                    user=username,
                    page=startpage,
                    limit=50)
    else:
        sys.exit("No config exist for this server, valid servers are: last.fm, libre.fm")


    url = baseurl + urllib.urlencode(urlvars)
    try:
        f = urllib2.urlopen(url)
    except:
        print "Failed to open page %s" % urlvars['page']
        response = None
        return response

    response = f.read()
    f.close()

    #bad hack to fix bad xml
    response = re.sub('\xef\xbf\xbe', '', response)
    return response

def get_pageinfo(response):
    """Check how many pages of tracks the user have."""
    xmlpage = minidom.parseString(response)
    totalpages = xmlpage.getElementsByTagName('recenttracks')[0].attributes['totalPages'].value
    return int(totalpages)

def get_tracklist(response):
    """Read XML page and get a list of tracks and their info."""
    xmlpage = minidom.parseString(response)
    tracklist = xmlpage.getElementsByTagName('track')
    return tracklist

def parse_track(tracklist, i):
    """Extract info from every track entry and output to list."""
    track = tracklist[i].getElementsByTagName
    try:
        artistname = track('artist')[0].childNodes[0].data
    except:
        artistname = ''
    try:
        artistmbid = track('artist')[0].attributes['mbid'].value
    except:
        artistmbid = ''
    try:
        trackname = track('name')[0].childNodes[0].data
    except:
        trackname = ''
    try:
        trackmbid = track('mbid')[0].childNodes[0].data
    except:
        trackmbid = ''
    try:
        albumname = track('album')[0].childNodes[0].data
    except:
        albumname = ''
    try:
        albummbid = track('album')[0].attributes['mbid'].value
    except:
        albummbid = ''
    try:
        date = track('date')[0].attributes['uts'].value
    except:
        date = ''

    output = [date, trackname, artistname, albumname, trackmbid, artistmbid, albummbid]

    return output

def write_tracks(trackdict, outfile, startpage, page, totalpages):
    """Write dictionary content with all tracks to file."""
    #create a sorted list from track dictionary.
    sortlist = []
    for v in trackdict.values():
        sortlist.append(v)
    sortlist.sort(reverse=True)

    #open output file and write tracks.
    f = open(outfile, 'a')
    for i in sortlist:
        #sys.stdout.write(("\t".join(trackdict[i]) + "\n").encode('utf-8'))
        f.write(("\t".join(i) + "\n").encode('utf-8'))
    print "Wrote page %s-%s of %s to file %s, exiting." % (startpage, page, totalpages, outfile)
    f.close()

def main(username, startpage, outfile):
    trackdict = dict()
    page = startpage
    response = connect_server(username, page)
    totalpages = get_pageinfo(response)
    #totalpages = 2

    if startpage > totalpages:
        sys.exit("First page (%s) is higher than total pages (%s), exiting." % (startpage, totalpages))

    while page <= totalpages:
        #Skip connect if on first page, already have that one stored.
        if page > startpage:
            response =  connect_server(username, page)
            #If empty response, something went wrong, write tracks to file and exit.
            if not response:
                write_tracks(trackdict, outfile, startpage, page-1, totalpages)
                sys.exit()

        tracklist = get_tracklist(response)
        for i in range(len(tracklist)):
            track = parse_track(tracklist, i)
            trackdict.setdefault(track[0], track)
        
        if (page % 10) == 0:
            print "Getting page %s of %s.." % (page, totalpages)

        page += 1
        time.sleep(.5)
    

    write_tracks(trackdict, outfile, startpage, page-1, totalpages)

if __name__ == "__main__":
    parser = OptionParser()
    username, outfile, startpage, server = get_options(parser)
    main(username, startpage, outfile)

