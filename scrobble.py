try:
    import hashlib
    md5hash = hashlib.md5
except ImportError:
    import md5
    md5hash = md5.new

from optparse import OptionParser
import time

import socket
import errno

from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


class ScrobbleException(Exception):
    pass


class ScrobbleServer(object):

    def __init__(self, server_name, username, password, client_code='imp'):
        if server_name[:7] != "http://":
            server_name = f"http://{server_name}"
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
        token = (md5hash((md5hash(
                self.password.encode('utf-8')).hexdigest()
                + str(timestamp)).encode('utf-8'))
                .hexdigest())

        auth_url = f"{self.name}/?hs=true&p=1.2&u={self.username}&t={timestamp}&a={token}&c={self.client_code}"
        response = urlopen(auth_url).read().decode('utf-8')
        lines = response.split("\n")
        if lines[0] != "OK":
            raise ScrobbleException(f'Server returned: {response}')
        self.session_id = lines[1]
        self.submit_url = lines[3]

    def submit(self, sleep_func=time.sleep):
        if len(self.post_data) == 0:
            return
        i = 0
        data = []
        for track in self.post_data:
            data += track.get_tuples(i)
            i += 1
        data += [('s', self.session_id)]
        last_error = None
        for timeout in (10, 20, 40, 60, 90, 120):
            try:
                response = urlopen(self.submit_url, urlencode(data)).read()
                response = response.strip()
            except (URLError, HTTPError) as e:
                last_error = str(e)
                print('Scrobbling error: {last_error}, will retry in {timeout}s')
            except socket.error as error:
                        if error.errno == errno.WSAECONNRESET:
                              last_error = str(error)
                              print('Scrobbling error: {last_error}, will retry in timeouts')

            else:
                if response == 'OK':
                    break
                else:
                    try:
                        last_error = f'Bad server response: {response}'
                    except:
                        last_error = 'Unknown server response.'
                    print(f'{last_error}, will retry in {timeout}s')
            sleep_func(timeout)
        else:
            raise ScrobbleException(f'Cannot scrobble after multiple retries. Last error: {last_error}')

        self.post_data = []
        sleep_func(1)

    def add_track(self, scrobble_track, sleep_func=time.sleep):
        i = len(self.post_data)
        if i > 49:
            self.submit(sleep_func)
            i = 0
        self.post_data.append(scrobble_track)


class ScrobbleTrack(object):

    def __init__(self, timestamp, trackname, artistname, albumname=None,
                 trackmbid=None, tracklength=None, tracknumber=None):
        self.timestamp = timestamp
        self.trackname = trackname
        self.artistname = artistname
        self.albumname = albumname
        self.trackmbid = trackmbid
        self.tracklength = tracklength
        self.tracknumber = tracknumber

    def get_tuples(self, i):
        #timestamp = str(int(time.mktime(self.timestamp.utctimetuple())))
        data = []
        data += [(f'i[{i}]', self.timestamp), (f't[{i}]', self.trackname),
                 (f'a[{i}]', self.artistname)]
        if self.albumname is not None:
            data.append((f'b[{i}]', self.albumname))
        if self.trackmbid is not None:
            data.append((f'm[{i}]', self.trackmbid))
        if self.tracklength is not None:
            data.append((f'l[{i}]', self.tracklength))
        if self.tracknumber is not None:
            data.append((f'n[{i}]', self.tracknumber))
        return data


def get_parser(usage):
    parser = OptionParser(usage=usage)
    parser.add_option('-s', '--server',
                      help="Server to submit to.  Defaults to"
                           " 'turtle.libre.fm'.")
    parser.set_defaults(server='turtle.libre.fm')
    return parser
