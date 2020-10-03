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
# Downloaded from: https://github.com/encukou/lastscrape-gui/blob/master/lastexport.py
# Does not work with Python2
#

"""
Script for exporting tracks through audioscrobbler API.
Usage: lastexport.py -u USER [-o OUTFILE] [-p STARTPAGE] [-s SERVER] [-f FROMUTS] [-z TOUTS]
"""
import pdb
import urllib.request, urllib.error, urllib.parse, urllib.request, urllib.parse, urllib.error, sys, time, re
import xml.etree.ElementTree as ET
from optparse import OptionParser

__version__ = '0.0.5'

def get_options(parser):
    """ Define command line options."""
    parser.add_option("-u", "--user", dest="username", default=None,
                      help="User name.")
    parser.add_option("-o", "--outfile", dest="outfile", default="exported_tracks.txt",
                      help="Output file, default is exported_tracks.txt")
    parser.add_option("-p", "--page", dest="startpage", type="int", default="1",
                      help="Page to start fetching tracks from, default is 1")
    parser.add_option("-f", "--from", dest="fromuts", type="int", default=None,
                      help="Unix timestamp - only display scrobbles after this time, default is none")
    parser.add_option("-z", "--to", dest="touts", type="int", default=None,
                      help="Unix timestamp - only display scrobbles after this time, default is none")
    parser.add_option("-s", "--server", dest="server", default="last.fm",
                      help="Server to fetch track info from, default is last.fm")
    parser.add_option("-t", "--type", dest="infotype", default="scrobbles",
                      help="Type of information to export, scrobbles|loved|banned, default is scrobbles")
    options, args = parser.parse_args()

    if not options.username:
        sys.exit("User name not specified, see --help")

    if options.infotype == "loved":
        infotype = "lovedtracks"
    elif options.infotype == "banned":
        infotype = "bannedtracks"
    else:
        infotype = "recenttracks"
         
    return options.username, options.outfile, options.startpage, options.fromuts, options.touts, options.server, infotype

def connect_server(server, username, startpage, fromuts, touts, sleep_func=time.sleep, tracktype='recenttracks'):
    """ Connect to server and get a XML page."""
    if server == "libre.fm":
        baseurl = 'http://alpha.libre.fm/2.0/?'
        urlvars = dict(method='user.get%s' % tracktype,
                    api_key=('lastexport.py-%s' % __version__).ljust(32, '-'),
                    user=username,
                    page=startpage,
                    limit=200)

    elif server == "last.fm":
        baseurl = 'http://ws.audioscrobbler.com/2.0/?'
        urlvars = dict(method='user.get%s' % tracktype,
                    api_key='e38cc7822bd7476fe4083e36ee69748e',
                    user=username,
                    page=startpage,
                    limit=50)
        if fromuts:
            urlvars['from'] = fromuts
        if touts:
            urlvars['to'] = touts
            
    else:
        if server[:7] != 'http://':
            server = 'http://%s' % server
        baseurl = server + '/2.0/?'
        urlvars = dict(method='user.get%s' % tracktype,
                    api_key=('lastexport.py-%s' % __version__).ljust(32, '-'),
                    user=username,
                    page=startpage,
                    limit=200)

    url = baseurl + urllib.parse.urlencode(urlvars)
    for interval in (1, 5, 10, 62):
        try:
            f = urllib.request.urlopen(url)
            break
        except Exception as e:
            last_exc = e
            print("Exception occured, retrying in %ds: %s" % (interval, e))
            sleep_func(interval)
    else:
        print("Failed to open page %s" % urlvars['page'])
        raise last_exc

    response = f.read()
    f.close()

    #bad hack to fix bad xml
    response = re.sub('\xef\xbf\xbe', '', response.decode())
    # Unbelievably, some people have ASCII control characters
    # in their scrobbles: I ran across a \x04 (end of transmission).
    # Remove all of those except \n and \t
    response = re.sub('[\0-\x08\x0b-\x1f]', '', response)
    return response

def get_pageinfo(response, tracktype='recenttracks'):
    """Check how many pages of tracks the user have."""
    xmlpage = ET.fromstring(response)
    totalpages = xmlpage.find(tracktype).attrib.get('totalPages')
    return int(totalpages)

def get_tracklist(response):
    """Read XML page and get a list of tracks and their info."""
    xmlpage = ET.fromstring(response)
    tracklist = xmlpage.getiterator('track')
    return tracklist

def parse_track(trackelement):
    """Extract info from every track entry and output to list."""
    if trackelement.find('artist').getchildren():
        #artist info is nested in loved/banned tracks xml
        artistname = trackelement.find('artist').find('name').text
        artistmbid = trackelement.find('artist').find('mbid').text
    else:
        artistname = trackelement.find('artist').text
        artistmbid = trackelement.find('artist').get('mbid')

    if trackelement.find('album') is None:
        #no album info for loved/banned tracks
        albumname = ''
        albummbid = ''
    else:
        albumname = trackelement.find('album').text
        albummbid = trackelement.find('album').get('mbid')

    trackname = trackelement.find('name').text
    trackmbid = trackelement.find('mbid').text
    date = trackelement.find('date').get('uts')

    output = [date, trackname, artistname, albumname, trackmbid, artistmbid, albummbid]

    for i, v in enumerate(output):
        if v is None:
            output[i] = ''

    return output

def write_tracks(tracks, outfileobj):
    """Write tracks to an open file"""

    for fields in tracks:
        outfileobj.write("\t".join(fields) + "\n")

def get_tracks(server, username, fromuts, touts, startpage=1, sleep_func=time.sleep, tracktype='recenttracks'):
    page = startpage
    response = connect_server(server, username, page, fromuts, touts, sleep_func, tracktype)
    totalpages = get_pageinfo(response, tracktype)

    if startpage > totalpages:
        raise ValueError("First page (%s) is higher than total pages (%s)." % (startpage, totalpages))

    while page <= totalpages:
        #Skip connect if on first page, already have that one stored.

        if page > startpage:
            response =  connect_server(server, username, page, fromuts, touts, sleep_func, tracktype)

        tracklist = get_tracklist(response)
		
        tracks = []
        for trackelement in tracklist:
            # do not export the currently playing track.
            if "nowplaying" not in trackelement.attrib or not trackelement.attrib["nowplaying"]:
                tracks.append(parse_track(trackelement))

        yield page, totalpages, tracks

        page += 1
        sleep_func(.5)

def main(server, username, startpage, fromuts, touts, outfile, infotype='recenttracks'):
    trackdict = dict()
    page = startpage  # for case of exception
    totalpages = -1  # ditto
    n = 0
    try:
        for page, totalpages, tracks in get_tracks(server, username, fromuts, touts, startpage, tracktype=infotype):
            print("Got page %s of %s.." % (page, totalpages))
            for track in tracks:
                if infotype == 'recenttracks':
                    trackdict.setdefault(track[0], track)
                else:
                    #Can not use timestamp as key for loved/banned tracks as it's not unique
                    n += 1
                    trackdict.setdefault(n, track)
    except ValueError as e:
        exit(e)
    except Exception:
        raise
    finally:
        with open(outfile, 'a') as outfileobj:
            tracks = sorted(list(trackdict.values()), reverse=True)
            write_tracks(tracks, outfileobj)
            print("Wrote page %s-%s of %s to file %s" % (startpage, page, totalpages, outfile))

if __name__ == "__main__":
    parser = OptionParser()
    username, outfile, startpage, fromuts, touts, server, infotype = get_options(parser)
    main(server, username, startpage, fromuts, touts, outfile, infotype)
