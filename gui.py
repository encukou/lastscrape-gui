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
import lastexport
import scrobble
from datetime import datetime
import collections

__version__ = '0.0.6'

def report_error(backtrace):
        errordialog = QtGui.QDialog()
        layout = QtGui.QVBoxLayout(errordialog)
        layout.addWidget(QtGui.QLabel(
                "We're sorry, but there was an error.\n"
                "If you report it at the adderss given below, "
                "maybe it can be fixed.\n"
            ))
        textarea = QtGui.QTextEdit()
        backtrace = ("\nPlease report the bug at:\n"
                + " https://github.com/encukou/lastscrape-gui/issues/new\n\n"
                + backtrace
            )
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
        except Exception as e:
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
        self.scrobbles = TracksModel()
        self.tvScrobbles1.setModel(self.scrobbles)
        self.tvScrobbles2.setModel(self.scrobbles)
        self.tvScrobbles3.setModel(self.scrobbles)
        self.enableTabs(True, False, False, False)
        self.twTabs.setCurrentWidget(self.tabInfo)
        self.cbServer.addItem('turtle.libre.fm')
        self.cbServer.addItem('turtle.dev.libre.fm')
        self.cbScrapeSource.addItem('last.fm')
        self.cbScrapeSource.addItem('libre.fm')

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
                                     "Nag",
                                     "Please put in your username")
            return
        if self.worker: return
        self.cancel_loads()
        self.scrobbles.clear()
        self.lblScrapeStatus.setText('Initializing...')
        self.enableTabs(False, True, False, False)
        self.pgUpload.hide()
        self.bpLoad.show()
        self.twTabs.setCurrentWidget(self.tabGrab)
        self.worker = worker = ScraperThread(username, self.cbScrapeSource.currentText())
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
        self.saveToFile()
        self.lblCleanupStatus.setText("Done? Let's find them a new home.")
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
                track = line.strip('\r\n').split('\t')
                tracks.append( track )
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
        self.saveToFile()

    def saveToFile(self):
        filename = self.txtFilename.text()
        print('Saving to %s' % self.txtFilename.text())
        with open(filename, 'w') as outfile:
            lastexport.write_tracks(self.scrobbles.tracklist, outfile)
        self.twTabs.setCurrentWidget(self.tabPush)

    @errors_reported
    @QtCore.pyqtSignature("")
    def on_btnImport_clicked(self, *args):
        if args: return
        if self.uploader: return
        try:
            server = str(self.cbServer.currentText())
            username = str(self.txtLibreUsername.text()).replace(' ','+')
            password = str(self.txtLibrePassword.text())
            scrobbler = scrobble.ScrobbleServer(
                    server_name = server,
                    username = username,
                    password = password,
                    client_code = 'imp',
                )
        except Exception as e:
            QtGui.QMessageBox.warning(self, "Oops", "Couldn't connect to the "
                "server. Please check your username and password.\n\n" +
                str(e)[:256])
            return
        self.uploader = uploader = PushThread(scrobbler, self.scrobbles.tracklist)
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
        self.lblUploadProgress.setText("%d tracks pushed!" % num)
    def uploader_done(self):
        self.uploader = None
        self.enableTabs()
        self.pgUpload.hide()
        QtGui.QMessageBox.information(self, "Done!", "They've all been "
                "uploaded! Thanks for your time.")
        self.scrobbles.clear()
    def uploader_killed(self):
        self.uploader = None
        self.enableTabs()
        self.pgUpload.hide()

    @errors_reported
    def add_tracks(self, tracks):
        if not tracks: return
        self.scrobbles.addTracks(tracks)
        lasttime = self.scrobbles.tracklist[-1][0]
        niceDate = QtCore.QDateTime.fromTime_t(int(lasttime)).toString()
        self.lblScrapeStatus.setText('Scraped %d tracks, last one from %s' %
            (self.scrobbles.rowCount(), niceDate))
        self.lblCleanupStatus.setText('Read %d tracks, last one from %s' %
            (self.scrobbles.rowCount(), niceDate))

class TracksModel(QtCore.QAbstractTableModel):
    columntitles = "Time, Track name, Artist name, Album name, Track MBID, Artist MBID, Album MBID".split(',')

    def __init__(self):
        QtCore.QAbstractTableModel.__init__(self)
        self.tracklist = []
        self.dateset = set()

    def rowCount(self, index=QtCore.QModelIndex()):
        if index.isValid(): return 0
        return len(self.tracklist)

    def columnCount(self, index=QtCore.QModelIndex()):
        if index.isValid(): return 0
        return len(self.columntitles)

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid(): return None
        if index.parent().isValid(): return None
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        row = self.tracklist[index.row()]
        data = row[index.column()]
        if index.column() == 0:
            return QtCore.QDateTime.fromTime_t(int(data))
        return data

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal: return None
        if role != Qt.DisplayRole: return None
        return self.columntitles[section].strip()

    def setData(self, index, data, role=Qt.EditRole):
        if not index.isValid(): return False
        if index.parent().isValid(): return False
        if role != Qt.EditRole: return False
        row = index.row()
        column = index.column()
        track = self.tracklist[row]
        if column == 0:
            val = str(data.toDateTime().toTime_t())
        else:
            val = str(data.toString())
        if val:
            track[column] = val
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
            if len(track) != len(self.columntitles):
                print(track)
                raise AssertionError("%s items of information in track is not %s" % (len(track), len(self.columntitles)))
            if track[0] in self.dateset:
                print("Duplicate track: %s" % (track,))
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
    def __init__(self, username, server, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.username = username
        self.server = server

    def run(self):
        try:
            for page, totalpages, tracks in lastexport.get_tracks(
                    self.server,
                    self.username,
                    sleep_func=lambda s: self.msleep(int(s * 1000)),
                ):
                self.emit(QtCore.SIGNAL("freshTracks"), tracks)
        except Exception as e:
            import traceback
            backtrace = traceback.format_exc(e)
            self.emit(QtCore.SIGNAL("error"), backtrace)
            #break #simulate

class PushThread(QtCore.QThread):
    def __init__(self, scrobbler, tracks, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.scrobbler = scrobbler
        self.tracks = tracks

    def run(self):
        try:
            for track in self.tracks:
                track = [item.encode('utf-8') for item in track]
                timestamp, trackname, artistname, albumname, trackmbid, artistmbid, albummbid = track
                self.scrobbler.add_track(scrobble.ScrobbleTrack(timestamp, trackname, artistname, albumname, trackmbid))
                self.emit(QtCore.SIGNAL("progress"), (timestamp, trackname, artistname, albumname, trackmbid))
            self.scrobbler.submit(sleep_func=lambda s: self.msleep(int(s * 1000)))
        except Exception as e:
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

