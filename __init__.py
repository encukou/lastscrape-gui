try:
    from lastscrape.lastscrape import *
except ImportError:
    from lastscrape import *


if __name__ == '__main__':
    from . import gui
    import sys
    gui.main(*sys.argv)