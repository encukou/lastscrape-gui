try:
    import hashlib
    md5hash = hashlib.md5
except ImportError:
    import md5
    md5hash = md5.new
from optparse import OptionParser
import time
from urllib import urlencode
from urllib2 import urlopen


class GobbleException(Exception):

    pass


class GobbleServer(object):

    def __init__(self, server_name, username, password, client_code='imp'):
        if server_name[:7] != "http://":
            server_name = "http://%s" % (server_name,)
        self.client_code = client_code
        self.name = server_name
        self.password = password
        self.post_data = []
        self.session_id = None
        self.submit_url = None
        self.username = username
        self._handshake()


    def _handshake(self):
        timestamp = int(time.time())
        token = (md5hash(md5hash(self.password).hexdigest()
                    + str(timestamp)).hexdigest())
        auth_url = "%s/?hs=true&p=1.2&u=%s&t=%d&a=%s&c=%s" % (self.name,
                                                              self.username,
                                                              timestamp,
                                                              token,
                                                              self.client_code)
        response = urlopen(auth_url).read()
        lines = response.split("\n")
        if lines[0] != "OK":
            raise GobbleException("Server returned: %s" % (response,))
        self.session_id = lines[1]
        self.submit_url = lines[3]

    def submit(self):
        if len(self.post_data) == 0:
            return
        i = 0
        data = []
        for track in self.post_data:
            data += track.get_tuples(i)
            i += 1
        data += [('s', self.session_id)]
        response = urlopen(self.submit_url, urlencode(data)).read()
        if response != "OK\n":
            raise GobbleException("Server returned: %s" % (response,))
        self.post_data = []
        time.sleep(1)

    def add_track(self, gobble_track):
        i = len(self.post_data)
        if i > 49:
            self.submit()
            i = 0
        self.post_data.append(gobble_track)


class GobbleTrack(object):

    def __init__(self, artist, track, timestamp, album=None, length=None,
                 tracknumber=None, mbid=None):
        self.artist = artist
        self.track = track
        self.timestamp = timestamp
        self.album = album
        self.length = length
        self.tracknumber = tracknumber
        self.mbid = mbid

    def get_tuples(self, i):
        timestamp = str(int(time.mktime(self.timestamp.utctimetuple())))
        data = []
        data += [('a[%d]' % i, self.artist), ('t[%d]' % i, self.track),
                 ('i[%d]' % i, timestamp)]
        if self.album is not None:
            data.append(('b[%d]' % i, self.album))
        if self.length is not None:
            data.append(('l[%d]' % i, self.length))
        if self.tracknumber is not None:
            data.append(('n[%d]' % i, self.tracknumber))
        if self.mbid is not None:
            data.append(('m[%d]' % i, self.mbid))
        return data


def get_parser(usage):
    parser = OptionParser(usage=usage)
    parser.add_option('-s', '--server',
                      help="Server to submit to.  Defaults to"
                           " 'turtle.libre.fm'.")
    parser.set_defaults(server='turtle.libre.fm')
    return parser
