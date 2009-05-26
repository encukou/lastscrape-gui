#! /usr/bin/python
# Encoding: UTF-8

#
# Lastscrape GUI -- GUI for Lascscrape
# Copyright (C) 2009 Petr Viktorin
# (copyright will be assigned to FSF as soon as the papers come...)
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

import sys
from PyQt4 import QtCore, QtGui, uic
from PyQt4.Qt import Qt
import lastscrape
import gobble
from datetime import datetime
import collections

__version__ = '0.0.3'

def report_error(backtrace):
        errordialog = QtGui.QDialog()
        layout = QtGui.QVBoxLayout(errordialog)
        layout.addWidget(QtGui.QLabel(
            u"We're sorry, but there was an error.\n"
            u"If you report it, maybe it can be fixed.\n"
            u"Just copy the text below and mail it to "
            u"<encukou@gmail.com>:")) #Change this if we become part of libre.fm
        textarea = QtGui.QTextEdit()
        textarea.setText(backtrace)
        textarea.setReadOnly(True)
        layout.addWidget(textarea)
        closebutton = QtGui.QPushButton('Quit')
        errordialog.connect(closebutton, QtCore.SIGNAL('clicked()'),
                            QtCore.SLOT('reject()'))
        layout.addWidget(closebutton)
        errordialog.exec_()
        QtGui.QApplication.exit()

def errors_reported(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            import traceback
            backtrace = traceback.format_exc(e)
            report_error(backtrace)
    return wrapper

class MainWindow(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.worker = None
        self.uploader = None
        self.cancel_loads = lambda:None
        uic.loadUi('lastscrape.ui', self)
        self.setWindowTitle("LastScrape GUI "+__version__)
        #self.connect(self.btnChangeFilename,
        #            QtCore.SIGNAL('clicked()'),
        #            self.changeFilename)
        self.scrobbles = TracksModel() #QtGui.QStandardItemModel(0, 3)
        self.tvScrobbles1.setModel(self.scrobbles)
        self.tvScrobbles2.setModel(self.scrobbles)
        self.tvScrobbles3.setModel(self.scrobbles)
        self.enableTabs(True, False, False, False)
        self.twTabs.setCurrentWidget(self.tabInfo)
        self.cbServer.addItem('turtle.libre.fm')
        self.cbServer.addItem('turtle.dev.libre.fm')

    def enableTabs(self, info=True, grab=False, cleanup=True, push=True, credits=True):
        self.twTabs.setTabEnabled(0, info)
        self.twTabs.setTabEnabled(1, grab)
        self.twTabs.setTabEnabled(2, cleanup)
        self.twTabs.setTabEnabled(3, push)
        self.twTabs.setTabEnabled(4, credits)

    @errors_reported
    @QtCore.pyqtSignature("")
    def on_btnChangeFilename_clicked(self, *args):
        if args: return
        newFilename = QtGui.QFileDialog.getSaveFileName(self,
            "Save",
            self.txtFilename.text())
        if newFilename:
            self.txtFilename.setText(newFilename)

    @errors_reported
    @QtCore.pyqtSignature("")
    def on_btnGrab_clicked(self, *args):
        if args: return
        username = self.txtUsername.text()
        if not username:
            QtGui.QMessageBox.warning(self,
                                     u"Nag",
                                     u"Please put in your username")
            return
        if self.worker: return
        self.cancel_loads()
        self.scrobbles.clear()
        self.lblScrapeStatus.setText('Initializing...')
        self.enableTabs(False, True, False, False)
        self.pgUpload.hide()
        self.bpLoad.show()
        self.twTabs.setCurrentWidget(self.tabGrab)
        self.worker = worker = ScraperThread(username)
        self.connect(worker, QtCore.SIGNAL("freshTracks"), self.add_tracks)
        self.connect(worker, QtCore.SIGNAL("error"), report_error)
        self.connect(worker, QtCore.SIGNAL("finished()"), self.worker_done)
        self.connect(worker, QtCore.SIGNAL("terminated()"), self.worker_killed)
        worker.start()
    def worker_done(self):
        self.worker = None
        self.enableTabs()
        self.twTabs.setCurrentWidget(self.tabCleanup)
        self.bpLoad.hide()
        self.lblCleanupStatus.setText(u"Done? Let's find them a new home.")
    def worker_killed(self):
        self.worker = None
        self.enableTabs(True, False, False, False)
        self.twTabs.setCurrentWidget(self.tabInfo)

    @errors_reported
    @QtCore.pyqtSignature("")
    def on_btnToCleanup_clicked(self, *args):
        if args: return
        self.btnSave.setEnabled(False)
        self.cancel_loads()
        self.scrobbles.clear()
        exiting = [False]
        def cancel_loads():
            exiting[0] = True
        self.cancel_loads = cancel_loads
        self.enableTabs(True, False, True, False)
        self.bpLoad.show()
        self.twTabs.setCurrentWidget(self.tabCleanup)
        infile = open(self.txtFilename.text())
        try:
            tracks = []
            for line in infile:
                artist, track, timestamp = line.strip().split('\t')
                artist = artist.decode('UTF-8')
                track = track.decode('UTF-8')
                dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
                tracks.append( (artist, track, dt) )
                if len(tracks)>=250:
                    QtGui.QApplication.processEvents()
                    if exiting[0]:
                        break
                    self.add_tracks(tracks)
                    tracks = []
            self.add_tracks(tracks)
            self.bpLoad.hide()
            self.cancel_loads = lambda:None
            self.enableTabs()
            self.lblCleanupStatus.setText(
                "When you're done, save and upload your scrobbles.")
            self.btnSave.setEnabled(True)
        finally:
            infile.close()

    @errors_reported
    @QtCore.pyqtSignature("")
    def on_btnSave_clicked(self, *args):
        if args: return
        outfile = open(self.txtFilename.text(), 'w')
        try:
            for artist, track, timestamp in self.scrobbles.tracklist:
                dt = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
                line = u'%s\t%s\t%s\n' % (artist, track, dt)
                outfile.write(line.encode('utf-8'))
        finally:
            outfile.close()
        self.twTabs.setCurrentWidget(self.tabPush)

    @errors_reported
    @QtCore.pyqtSignature("")
    def on_btnImport_clicked(self, *args):
        if args: return
        if self.uploader: return
        try:
            server = unicode(self.cbServer.currentText())
            username = unicode(self.txtLibreUsername.text()).replace(' ','+')
            password = unicode(self.txtLibrePassword.text())
            gobbler = gobble.GobbleServer(
                    server_name = server,
                    username = username,
                    password = password,
                    client_code = 'imp',
                )
        except Exception, e:
            QtGui.QMessageBox.warning(self, u"Oops", u"Couldn't connect to the "
                u"server. Please check your username and password.\n\n" + 
                str(e)[:256])
            return
        self.uploader = uploader = PushThread(gobbler, self.scrobbles.tracklist)
        self.connect(uploader, QtCore.SIGNAL("progress"),
                               self.uploader_progress)
        self.connect(uploader, QtCore.SIGNAL("error"), report_error)
        self.connect(uploader, QtCore.SIGNAL("finished()"), self.uploader_done)
        self.connect(uploader, QtCore.SIGNAL("terminated()"),
                               self.uploader_killed)
        self.enableTabs(False, False, False)
        self.pgUpload.setMaximum(len(self.scrobbles.tracklist))
        self.pgUpload.setValue(0)
        self.pgUpload.show()
        uploader.start()
    def uploader_progress(self, track):
        num = self.pgUpload.value() + 1
        self.pgUpload.setValue(num)
        self.lblUploadProgress.setText(u"%d tracks pushed!" % num)
    def uploader_done(self):
        self.uploader = None
        self.enableTabs()
        self.pgUpload.hide()
        QtGui.QMessageBox.information(self, u"Done!", u"They've all been "
                u"uploaded! Thanks for your time.")
        self.scrobbles.clear()
    def uploader_killed(self):
        self.uploader = None
        self.enableTabs()
        self.pgUpload.hide()

    @errors_reported
    def add_tracks(self, tracks):
        if not tracks: return
        self.scrobbles.addTracks(tracks)
        lasttime = self.scrobbles.tracklist[-1][2]
        self.lblScrapeStatus.setText('Scraped %d tracks, last one from %s' %
            (self.scrobbles.rowCount(), lasttime))
        self.lblCleanupStatus.setText('Read %d tracks, last one from %s' %
            (self.scrobbles.rowCount(), lasttime))

class TracksModel(QtCore.QAbstractTableModel):
    def __init__(self):
        QtCore.QAbstractTableModel.__init__(self)
        self.tracklist = []
        self.dateset = set()

    def rowCount(self, index=QtCore.QModelIndex()):
        if index.isValid(): return 0
        return len(self.tracklist)

    def columnCount(self, index=QtCore.QModelIndex()):
        if index.isValid(): return 0
        return 3

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid(): return QtCore.QVariant()
        if index.parent().isValid(): return QtCore.QVariant()
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return QtCore.QVariant()
        row = self.tracklist[index.row()]
        if index.column() == 2:
            return QtCore.QVariant(QtCore.QDateTime(row[2]))
        return QtCore.QVariant(row[index.column()])

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal: return QtCore.QVariant()
        if role != Qt.DisplayRole: return QtCore.QVariant()
        return QtCore.QVariant([u"Artist", u"Track", u"Time"][section])

    def setData(self, index, data, role=Qt.EditRole):
        if not index.isValid(): return False
        if index.parent().isValid(): return False
        if role != Qt.EditRole: return False
        row = index.row()
        column = index.column()
        track = self.tracklist[row]
        if column == 2:
            val = data.toDateTime().toPyDateTime()
            newtrack = (track[0], track[1], val)
        else:
            val = unicode(data.toString())
            if column == 0:
                newtrack = (val, track[1], track[2])
            else:
                newtrack = (track[0], val, track[2])
        if val:
            self.tracklist[row] = newtrack
            self.emit(QtCore.SIGNAL('dataChanged(QModelIndex,QModelIndex)'),
                index, index)
            return True
        else:
            return False

    def removeRow(self, row, parent):
        if parent.isValid(): return False
        self.beginRemoveRows(row)
        self.tracklist[row:row+1] = []
        self.endRemoveRows()

    def addTracks(self, tracks_in):
        tracks = []
        for track in tracks_in:
            if track[2] in self.dateset:
                print "Duplicate track: %s" % (track,)
            else:
                tracks.append(track)
                self.dateset.add(track[2])
        if not tracks: return
        oldRowCount = self.rowCount()
        newLastRow = oldRowCount+len(tracks)-1
        self.beginInsertRows(QtCore.QModelIndex(), oldRowCount, newLastRow)
        self.tracklist += tracks
        self.endInsertRows()

    def clear(self):
        self.tracklist = []
        self.dateset = set()
        self.reset()

    def flags(self, index):
        return (Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsEditable |
                Qt.ItemIsSelectable)

class ScraperThread(QtCore.QThread):
    def __init__(self, username, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.username = username

    def run(self):
        try:
            for artist, track, timestamp in lastscrape.fetch_tracks(
                    self.username,
                    request_delay=1,
                    sleep_func=self.sleep):
                dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
                self.emit(QtCore.SIGNAL("freshTracks"), [(artist, track, dt)])
        except Exception, e:
            import traceback
            backtrace = traceback.format_exc(e)
            self.emit(QtCore.SIGNAL("error"), backtrace)
            #break #simulate

class PushThread(QtCore.QThread):
    def __init__(self, gobbler, tracks, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.gobbler = gobbler
        self.tracks = tracks

    def run(self):
        try:
            for artist, track, dt in self.tracks:
                artist = artist.encode('UTF-8')
                track = track.encode('UTF-8')
                self.gobbler.add_track(gobble.GobbleTrack(artist, track, dt))
                self.emit(QtCore.SIGNAL("progress"), (artist, track, dt))
            self.gobbler.submit()
        except Exception, e:
            import traceback
            backtrace = traceback.format_exc(e)
            self.emit(QtCore.SIGNAL("error"), backtrace)

def main(*args):
    app = QtGui.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main(*sys.argv)
 
