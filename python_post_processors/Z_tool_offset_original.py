#!/usr/bin/python
from __future__ import print_function

__author__ = 'francesco'

import sys, os

BASE = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), ".."))
sys.path.insert(0, os.path.join(BASE, "lib", "python"))

import re

passthrough = []

replace = []

def progress(a, b):
    if os.environ.has_key("AXIS_PROGRESS_BAR"):
        print >> sys.stderr, "FILTER_PROGRESS=%d" % int(a * 100. / b + .5)
        sys.stderr.flush()


def main():
    count = 0
    infile = sys.argv[1]
    f = open(infile, "r")
    for line in f:
        print(line,end="")
        match = re.match("G21", line)
        if match:
           print("#<probe_height> = 19.3")

        match = re.match("M06(.*)T(\d\d)(.*)", line)
        if match:
            tool = float(match.group(2))
            print("G0 Z30")
            print("(MSG,Insert Z Probe)")
            print("M0")
            print("G38.2 Z0 F80")
            print("G10 P1 L20 Z[#<probe_height>]")
            print("G0 Z30")
            print("G54")
            print("(MSG,Remove Z Probe)")
            print("M0")
       
if __name__ == '__main__':
    main()

# vim:sw=4:sts=4:et:
