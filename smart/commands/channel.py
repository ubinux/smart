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
from smart.option import OptionParser, append_all
from smart.media import MediaSet
from smart.const import NEVER
from smart.channel import *
from smart import *
import textwrap
import sys, os

USAGE="smart channel [options]"

DESCRIPTION="""
This command allows one to manipulate channels. Channels are
used as sources of information about installed and available
packages. Depending on the channel type, a different backend
is used to handle interactions with the operating system and
extraction of information from the given channel.

The following channel types are available:

%(types)s

The following information is common to all channel types:

%(fields)s
"""

EXAMPLES="""
smart channel --help-type apt-rpm
smart channel --add mydb type=rpm-db name="RPM Database"
smart channel --add mychannel type=apt-rpm name="Some repository" \\
                  baseurl=http://somewhere.com/pub/repos components=extra
smart channel --set mychannel priority=-100
smart channel --disable mychannel
smart channel --remove mychannel
smart channel --show
smart channel --show mychannel > mychannel.txt
smart channel --add ./mychannel.txt
smart channel --add http://some.url/mychannel.txt
smart channel --add /mnt/cdrom
"""

def build_types():
    result = ""
    typeinfo = getAllChannelInfos().items()
    typeinfo.sort()
    for type, info in typeinfo:
        result += "  %-10s - %s\n" % (type, info.name)
    return result.rstrip()

def format_fields(fields):
    result = []
    maxkey = max([len(x[0]) for x in fields])
    for key, name, description in fields:
        if not description:
            description = name
        indent = " "*(5+maxkey)
        lines = textwrap.wrap(text=description, width=70,
                              initial_indent=indent,
                              subsequent_indent=indent)
        name = lines.pop(0).strip()
        result.append("  %s%s - %s" % (key, " "*(maxkey-len(key)), name))
        for line in lines:
            result.append(line)
    return "\n".join(result)

def parse_options(argv):
    description = DESCRIPTION % {"types": build_types(),
                                 "fields": format_fields(DEFAULTFIELDS)}
    parser = OptionParser(usage=USAGE,
                          description=description,
                          examples=EXAMPLES)
    parser.defaults["add"] = []
    parser.defaults["set"] = []
    parser.defaults["remove"] = []
    parser.defaults["enable"] = []
    parser.defaults["disable"] = []
    parser.defaults["show"] = None
    parser.add_option("--add", action="callback", callback=append_all,
                      help="argument is an alias and one or more "
                           "key=value pairs defining a channel, or a "
                           "filename/url pointing to a channel description "
                           "in the same format used by --show, or a "
                           "directory path where autodetection will be "
                           "tried")
    parser.add_option("--set", action="callback", callback=append_all,
                      help="argument is an alias, and one or more key=value "
                           "pairs modifying a channel")
    parser.add_option("--remove", action="callback", callback=append_all,
                      help="arguments are channel aliases to be removed")
    parser.add_option("--show", action="callback", callback=append_all,
                      help="show channels with given aliases, or all "
                           "channels if no arguments were given")
    parser.add_option("--enable", action="callback", callback=append_all,
                      help="enable channels with given aliases")
    parser.add_option("--disable", action="callback", callback=append_all,
                      help="disable channels with given aliases")
    parser.add_option("--force", action="store_true",
                      help="execute without asking")
    parser.add_option("--help-type", action="store", metavar="TYPE",
                      help="show further information about given type")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):

    channels = sysconf.get("channels", setdefault={})

    if opts.help_type:
        info = getChannelInfo(opts.help_type)
        print "Type:", opts.help_type, "-", info.name
        print
        print info.description.strip()
        print
        print "Custom Fields:"
        print format_fields(info.fields)
        print
        sys.exit(0)
    
    if opts.add:

        sysconf.assertWritable()

        if len(opts.add) == 1:
            arg = opts.add[0]
            if os.path.isdir(arg):
                newchannels = detectLocalChannels(arg)
            elif os.path.isfile(arg):
                newchannels = []
                data = open(arg).read()
                descriptions = parseChannelsDescription(data)
                for alias in descriptions:
                    channel = descriptions[alias]
                    channel["alias"] = alias
                    newchannels.append(channel)
            elif ":/" in arg:
                succ, fail = ctrl.downloadURLs([arg], "channel description")
                if fail:
                    raise Error, "Unable to fetch channel description: %s" \
                                 % fail[arg]
                data = open(succ[arg]).read()
                if succ[arg].startswith(sysconf.get("data-dir")):
                    os.unlink(succ[arg])
                newchannels = []
                descriptions = parseChannelsDescription(data)
                for alias in descriptions:
                    channel = descriptions[alias]
                    channel["alias"] = alias
                    newchannels.append(channel)
            else:
                raise Error, "File not found: %s" % arg
        else:
            alias = opts.add.pop(0).strip()
            if not alias:
                raise Error, "Channel has no alias"
            channel = {"alias": alias}
            for arg in opts.add:
                if "=" not in arg:
                    raise Error, "Argument '%s' has no '='" % arg
                key, value = arg.split("=")
                channel[key.strip()] = value.strip()
            if "type" not in channel:
                raise Error, "Channel has no type"
            newchannels = [channel]

        newaliases = []
        for channel in newchannels:
            type = channel.get("type")
            if not opts.force:
                info = getChannelInfo(type)
                print
                for field, name, descr in DEFAULTFIELDS:
                    if field in channel:
                        print "%s: %s" % (name, channel[field])
                for field, name, descr in info.fields:
                    if field in channel:
                        print "%s: %s" % (name, channel[field])
                print
            if opts.force or iface.askYesNo("Include this channel"):
                try:
                    createChannel(type, "alias", channel)
                except Error, e:
                    iface.error("Invalid channel: %s" % e)
                else:
                    try:
                        alias = channel.get("alias")
                        while not alias or alias in channels:
                            if alias:
                                print "Channel alias '%s' is already in use." \
                                      % alias
                            alias = raw_input("Channel alias: ").strip()
                        if "alias" in channel:
                            del channel["alias"]
                        channels[alias] = channel
                        newaliases.append(alias)
                    except KeyboardInterrupt:
                        print

        removable = [x for x in newaliases if channels[x].get("removable")]
        if removable:
            print
            print "Updating removable channels..."
            print
            import update
            updateopts = update.parse_options(removable)
            update.main(updateopts, ctrl)

    if opts.set:

        sysconf.assertWritable()

        if not opts.set:
            raise Error, "Invalid arguments"

        alias = opts.set.pop(0)
        if "=" in alias:
            raise Error, "First argument must be the channel alias"
        if alias not in channels:
            raise Error, "Channel with alias '%s' not found" % alias
        oldchannel = channels[alias]

        channel = {}
        for arg in opts.set:
            if "=" not in arg:
                raise Error, "Argument '%s' has no '='" % arg
            key, value = arg.split("=")
            key = key.strip()
            if key == "type":
                raise Error, "Can't change the channel type"
            if key == "alias":
                raise Error, "Can't change the channel alias"
            channel[key] = value.strip()

        newchannel = oldchannel.copy()
        newchannel.update(channel)
        for key in newchannel.keys():
            if not newchannel[key]:
                del newchannel[key]
        try:
            createChannel(newchannel.get("type"), alias, newchannel)
        except Error, e:
            raise Error, "Invalid channel: %s" % e

        oldchannel.update(channel)
        for key in oldchannel.keys():
            if not oldchannel[key]:
                del oldchannel[key]

    if opts.remove:

        sysconf.assertWritable()

        for alias in opts.remove:
            if alias not in channels:
                continue
            if opts.force or iface.askYesNo("Remove channel '%s'" % alias):
                del channels[alias]

    if opts.enable:

        sysconf.assertWritable()

        for alias in opts.enable:
            if alias not in channels:
                continue
            channel = channels[alias]
            if "disabled" in channel:
                del channel["disabled"]

    if opts.disable:

        sysconf.assertWritable()

        for alias in opts.disable:
            if alias not in channels:
                continue
            channels[alias]["disabled"] = "yes"

    if opts.show is not None:

        for alias in opts.show or channels:
            if alias not in channels:
                continue
            channel = channels[alias]
            desc = createChannelDescription(channel.get("type"),
                                            alias, channel)
            if desc:
                print desc
                print

# vim:ts=4:sw=4:et