python setup.py py2exe
mkdir lastscrape-win32
xcopy dist lastscrape-win32
cd lastscrape-win32
del lastscrape-win32.zip
7z a -mx7 -tzip lastscrape-win32.zip *
copy lastscrape-win32.zip ..
cd ..