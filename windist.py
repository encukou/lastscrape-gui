import subprocess
import os
import sys
import shutil
from .gui import __version__

dist_dir = 'lastscrape-win32-'+__version__
zip_name = dist_dir+'.zip'

subprocess.call([sys.executable, 'setup.py', 'py2exe'])
try:
    os.mkdir('dist_dir')
except WindowsError:
    pass
try:
    shutil.rmtree(dist_dir)
except WindowsError:
    pass
shutil.copytree('dist', dist_dir)
try:
    os.unlink(zip_name)
except WindowsError:
    pass
subprocess.call(['7z', 'a', '-mx7', '-tzip', zip_name, dist_dir])
