#!/usr/bin/python
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

import os.path
import sys
sys.path.append(os.path.join(sys.path[0], '../scripts'))

from datetime import datetime
import getpass
from gobble import get_parser, GobbleServer, GobbleTrack
import time
from urllib import urlencode
from urllib2 import urlopen


if __name__ == '__main__':
    usage = "%prog [-s <SERVER>] <USERNAME> <SCROBBLE DUMP>"
    parser = get_parser(usage=usage)
    opts,args = parser.parse_args()
    if len(args) != 2:
        parser.error("All arguments are required.")

    username,data = args
    server = opts.server
    password = getpass.getpass()
    gobbler = GobbleServer(server, username, password)

    for line in file(data):
        artist,track,timestamp = line.strip().split("\t")
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        gobbler.add_track(GobbleTrack(artist, track, dt))
        print "Adding to post %s playing %s" % (artist, track)
    gobbler.submit()
