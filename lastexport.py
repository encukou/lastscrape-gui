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

__version__ = '0.0.2'

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

def connect_server(server, username, startpage, sleep_func=time.sleep):
    """ Connect to server and get a XML page."""
    if server == "libre.fm":
        baseurl = 'http://alpha.libre.fm/2.0/?'
        urlvars = dict(method='user.getrecenttracks',
                    api_key=('lastexport.py-%s' % __version__).ljust(32, '-'),
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
        if server[:7] != 'http://':
            server = 'http://%s' % server
        baseurl = server + '/2.0/?'
        urlvars = dict(method='user.getrecenttracks',
                    api_key=('lastexport.py-%s' % __version__).ljust(32, '-'),
                    user=username,
                    page=startpage,
                    limit=200)

    url = baseurl + urllib.urlencode(urlvars)
    for interval in (1, 5, 10, 62):
        try:
            f = urllib2.urlopen(url)
            break
        except Exception, e:
            last_exc = e
            print "Exception occured, retrying in %ds: %s" % (interval, e)
            sleep_func(interval)
    else:
        print "Failed to open page %s" % urlvars['page']
        raise last_exc

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

def parse_track(trackelement):
    """Extract info from every track entry and output to list."""
    track = trackelement.getElementsByTagName
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

def write_tracks(tracks, outfileobj):
    """Write tracks to an open file"""
    for fields in tracks:
        outfileobj.write(("\t".join(fields) + "\n").encode('utf-8'))

def get_tracks(server, username, startpage=1, sleep_func=time.sleep):
    page = startpage
    response = connect_server(server, username, page, sleep_func)
    totalpages = get_pageinfo(response)

    if startpage > totalpages:
        raise ValueError("First page (%s) is higher than total pages (%s)." % (startpage, totalpages))

    while page <= totalpages:
        #Skip connect if on first page, already have that one stored.

        if page > startpage:
            response =  connect_server(server, username, page, sleep_func)

        tracklist = get_tracklist(response)
        tracks = [parse_track(trackelement) for trackelement in tracklist]

        yield page, totalpages, tracks

        page += 1
        sleep_func(.5)

def main(server, username, startpage, outfile):
    trackdict = dict()
    page = startpage  # for case of exception
    totalpages = -1  # ditto
    try:
        for page, totalpages, tracks in get_tracks(server, username, startpage):
            print "Got page %s of %s.." % (page, totalpages)
            for track in tracks:
                trackdict.setdefault(track[0], track)
    except ValueError, e:
        exit(e)
    except Exception:
        raise
    finally:
        with open(outfile, 'a') as outfileobj:
            tracks = sorted(trackdict.values(), reverse=True)
            write_tracks(tracks, outfileobj)
            print "Wrote page %s-%s of %s to file %s" % (startpage, page, totalpages, outfile)

if __name__ == "__main__":
    parser = OptionParser()
    username, outfile, startpage, server = get_options(parser)
    main(server, username, startpage, outfile)

