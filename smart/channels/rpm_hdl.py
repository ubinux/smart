#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
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
from smart.backends.rpm.header import RPMHeaderListLoader
from smart.const import SUCCEEDED, FAILED, NEVER
from smart.util.filetools import getFileDigest
from smart.channel import PackageChannel
from smart import *
import posixpath

class RPMHeaderListChannel(PackageChannel):

    def __init__(self, hdlurl, baseurl, *args):
        super(RPMHeaderListChannel, self).__init__(*args)
        self._hdlurl = hdlurl
        self._baseurl = baseurl

    def getCacheCompareURLs(self):
        return [self._hdlurl]

    def getFetchSteps(self):
        return 1

    def fetch(self, fetcher, progress):
        fetcher.reset()
        item = fetcher.enqueue(self._hdlurl, uncomp=True)
        fetcher.run(progress=progress)
        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            digest = getFileDigest(localpath)
            if digest == self._digest:
                return True
            self.removeLoaders()
            loader = RPMHeaderListLoader(localpath, self._baseurl)
            loader.setChannel(self)
            self._loaders.append(loader)
        elif fetcher.getCaching() is NEVER:
            lines = [_("Failed acquiring information for '%s':") % self,
                     u"%s: %s" % (item.getURL(), item.getFailedReason())]
            raise Error, "\n".join(lines)
        else:
            return False

        digest = self._digest

        return True

def create(alias, data):
    return RPMHeaderListChannel(data["hdlurl"],
                                data["baseurl"],
                                data["type"],
                                alias,
                                data["name"],
                                data["manual"],
                                data["removable"],
                                data["priority"])

# vim:ts=4:sw=4:et
