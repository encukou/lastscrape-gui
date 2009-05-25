#!/usr/bin/env python
#-*- coding: utf-8 -*-
#
# Lastscrape -- recovers data from libre.fm
# Copyright (C) 2009 Free Software Foundation, Inc
#
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

"""usage: lastscrape.py USER [OUTPUT_FILE]"""
import sys
import time
import codecs
import urllib2
from BeautifulSoup import BeautifulSoup

sys.stdout = codecs.lookup('utf-8')[-1](sys.stdout)

def parse_page(page):
    """Parse a page of recently listened tracks and return a list."""
    soup = BeautifulSoup(urllib2.urlopen(page),
                         convertEntities=BeautifulSoup.HTML_ENTITIES)
    for row in soup.find('table', 'candyStriped tracklist').findAll('tr'):
        artist, track, timestamp = parse_track(row)
        # Tracks submitted before 2005 have no timestamp
        if artist and track:
            yield (artist, track, timestamp)


def parse_track(row):
    """Return a tuple containing track data."""
    try:
        track_info = row.find('td', 'subjectCell')
        artist, track = track_info.findAll('a')
        timestamp = row.find('abbr')['title']
        artist = artist.contents[0].strip()
        track = track.contents[0].strip()
        return (artist, track, timestamp)
    except:
        # Parsing failed
        print 'parsing failed'
        return (None, None, None)


def fetch_tracks(user, request_delay=0.5):
    """Fetch all tracks from a profile page and return a list."""
    url = 'http://last.fm/user/%s/tracks' % user
    try:
        f = urllib2.urlopen(url)
    except urllib2.HTTPError:
        raise Exception("Username probably does not exist.")
    soup = BeautifulSoup(urllib2.urlopen(url),
                         convertEntities=BeautifulSoup.HTML_ENTITIES)
    try:
        num_pages = int(soup.find('a', 'lastpage').contents[0])
    except:
        num_pages = 1
    for cur_page in range(1, num_pages + 1):
        try:
            tracks = parse_page(url + '?page=' + str(cur_page))
        except:
            time.sleep(1)
            tracks = parse_page(url + '?page=' + str(cur_page))
        for artist, track, timestamp in tracks:
            yield (artist, track, timestamp)
        if cur_page < num_pages:
            time.sleep(request_delay)


def main(*args):
    if len(args) == 2:
        # Print to stdout
        for artist, track, timestamp in fetch_tracks(args[1]):
            print u'%s\t%s\t%s' % (artist, track, timestamp)
    elif len(args) == 3:
        # Write to file
        f = codecs.open(args[2], 'w', 'utf-8')
        for artist, track, timestamp in fetch_tracks(args[1]):
            f.write(u'%s\t%s\t%s\n' % (artist, track, timestamp))
            print u'%s\t%s\t%s' % (artist, track, timestamp)
        f.close()
    else:
        print __doc__


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
