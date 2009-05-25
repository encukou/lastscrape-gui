all:
	echo 'Run `make archive` to make the tarball'

archive:
	tar -cvzf lastscrape.tgz --transform 's,^,lastscrape-beta/,' gui.py lastscrape.ui gobble.py lastscrape.py BeautifulSoup.py import.py
