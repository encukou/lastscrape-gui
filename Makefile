all:
	echo 'Run `make archive` to make the tarball'

archive:
	tar -cvzf lastscrape-0.0.4.tgz --transform 's,^,lastscrape-0.0.4/,' gui.py lastscrape.ui gobble.py lastscrape.py BeautifulSoup.py import.py
