from gepeto.transaction import Transaction, PolicyRemove, REMOVE
from gepeto.matcher import MasterMatcher
from gepeto.option import OptionParser
from gepeto import *
import string
import re

USAGE="gpt remove [options] packages"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
    ctrl.updateCache()
    cache = ctrl.getCache()
    trans = Transaction(cache, PolicyRemove)
    found = False
    for arg in opts.args:
        matcher = MasterMatcher(arg)
        for pkg in matcher.filter(cache.getPackages()):
            if pkg.installed:
                found = True
                trans.enqueue(pkg, REMOVE)
    if not found:
        raise Error, "No installed packages matched given arguments"
    iface.showStatus("Computing transaction...")
    trans.run()
    iface.hideStatus()
    if trans:
        ctrl.commitTransaction(trans)

# vim:ts=4:sw=4:et