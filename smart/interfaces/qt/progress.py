#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Anders F Bjorklund <afb@users.sourceforge.net>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from smart.util.strtools import ShortURL, sizeToStr
from smart.progress import Progress, INTERVAL
from smart.interfaces.qt import getPixmap
from smart import *
import qt
import posixpath
import thread
import time
import sys

class QtProgress(Progress, qt.QDialog):

    def __init__(self, hassub, parent=None):
        Progress.__init__(self)
        qt.QDialog.__init__(self, parent)

        self._hassub = hassub
        self._shorturl = ShortURL(50)
        self._ticking = False
        self._stopticking = False
        self._fetcher = None

        if hassub:
            self.setMinimumSize(500, 400)
        else:
            self.setMinimumSize(300, 80)

        self.setIcon(getPixmap("smart"))
        self.setCaption(_("Operation Progress"))

        vbox = qt.QVBoxLayout(self, 10, 10)

        self._topic = qt.QLabel(self)
        self._topic.setMinimumWidth(300) #HACK
        vbox.addWidget(self._topic)

        self._progressbar = qt.QProgressBar(self)
        self._progressbar.setPercentageVisible(True)
        vbox.addWidget(self._progressbar)

        if hassub:
            self._listview = qt.QListView(self)
            self._listview.setSorting(-1, False);
            self._listview.setSelectionMode(qt.QListView.NoSelection )
            self._listview.show()
            vbox.addWidget(self._listview)

            column = self._listview.addColumn(_("Progress"))
            self._listview.setColumnWidthMode(column, qt.QListView.Manual)
            self._listview.setColumnWidth(column, 110)
            column = self._listview.addColumn(_("Current"))
            self._currentcolumn = column
            column = self._listview.addColumn(_("Total"))
            self._totalcolumn = column
            column = self._listview.addColumn(_("Speed"))
            self._speedcolumn = column
            column = self._listview.addColumn(_("ETA"))
            self._etacolumn = column
            column = self._listview.addColumn(_("Description"))
            self._listview.setColumnWidthMode(column, qt.QListView.Manual)

            self._subiters = {}
            self._subindex = 0

            self._bbox = qt.QHBox(self)
            self._bbox.layout().addStretch(1)
            vbox.addWidget(self._bbox)
            
            button = qt.QPushButton(self._bbox)
            button.setText(_("Cancel"))
            button.hide()
            qt.QObject.connect(button, qt.SIGNAL ("clicked()"), self._cancel)

    def setFetcher(self, fetcher):
        if fetcher:
            self._bbox.show()
            self._fetcher = fetcher
        else:
            self._bbox.hide()
            self._fetcher = None

    def _cancel(self):
        if self._fetcher:
            self._fetcher.cancel()

    def tick(self):
        while not self._stopticking:
            self.lock()
            #while qt.QApplication.eventLoop().hasPendingEvents():
            #       qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)
            self.unlock()
            time.sleep(INTERVAL)
        self._ticking = False

    def start(self):
        Progress.start(self)

        self.setHasSub(self._hassub)
        self._ticking = True
        self._stopticking = False
        if self._hassub:
            self._listview.hideColumn(self._currentcolumn) 
            self._listview.hideColumn(self._totalcolumn) 
            self._listview.hideColumn(self._speedcolumn) 
            self._listview.hideColumn(self._etacolumn) 

        thread.start_new_thread(self.tick, ())

    def stop(self):
        self._stopticking = True
        while self._ticking: pass

        Progress.stop(self)

        if self._hassub:
            self._listview.clear()
            self._subiters.clear()
            self._subindex = 0

        self._shorturl.reset()

        qt.QDialog.hide(self)

    def expose(self, topic, percent, subkey, subtopic, subpercent, data, done):
        qt.QDialog.show(self)
        
        if self._hassub and subkey:
            if subkey in self._subiters:
                iter = self._subiters[subkey]
            else:
                iter = qt.QListViewItem(self._listview)
                self._subiters[subkey] = iter
                self._listview.ensureItemVisible(iter)

            current = data.get("current", "")
            if current:
                 self._listview.showColumn(self._currentcolumn)
            total = data.get("total", "")
            if total:
                 self._listview.showColumn(self._totalcolumn)
            if done:
                speed = ""
                eta = ""
            else:
                speed = data.get("speed", "")
                if speed:
                    self._listview.showColumn(self._speedcolumn)
                eta = data.get("eta", "")
                if eta:
                    self._listview.showColumn(self._etacolumn)
            if current or total or speed or eta:
                iter.setText(1, current)
                iter.setText(2, total)
                iter.setText(3, speed)
                iter.setText(4, eta)
                subtopic = self._shorturl.get(subtopic)
            iter.setText(0, str(subpercent))
            iter.setText(5, subtopic)

            self._listview.insertItem(iter)
        else:
            self._topic.setText('<b>'+topic+'</b>')
            self._progressbar.setProgress(percent, 100)
            if self._hassub:
                self._listview.repaint()
        
        self.update()
        while qt.QApplication.eventLoop().hasPendingEvents():
            qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)

def test():
    import sys, time

    prog = QtProgress(True)

    data = {"item-number": 0}
    total, subtotal = 20, 5
    
    prog.start()
    prog.setTopic("Installing packages...")
    for n in range(1,total+1):
        data["item-number"] = n
        prog.set(n, total)
        prog.setSubTopic(n, "package-name%d" % n)
        for i in range(0,subtotal+1):
            prog.setSub(n, i, subtotal, subdata=data)
            prog.show()
            time.sleep(0.01)
    prog.stop()


if __name__ == "__main__":
    app = qt.QApplication(sys.argv)
    test()

# vim:ts=4:sw=4:et
