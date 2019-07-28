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
    global feedrate, feedrat
    feedrate        = 0
    feedrate2       = 0
    tot_line_number = 0
    is_on           = True
    set_z           = False
    infile = sys.argv[1]
    f = open(infile, "r")
    for line in f:
        tot_line_number += 1
        match = re.match("T(\d{1,2})(.*)M(\d.*)", line)
        if match:
            tool = int(match.group(1))
            print("M101 P%d" % tool)
            print("T%d M6" % tool)
            if set_z:
                print("O100 call [%d]" % tool)
            else:
                with open('/home/ciccio/linuxcnc/configs/10060_3axis/routines/set_z.ngc', 'r') as z_tool_routine:
                     line_vector = z_tool_routine.readlines()
                line_vector[8] = str("  G10 L10 P%d Z[#<probe_height>]\n" % tool)
                with open('/home/ciccio/linuxcnc/configs/10060_3axis/routines/set_z.ngc', 'w') as z_tool_routine:
                     z_tool_routine.writelines(line_vector)
                z_tool_routine.close()
                tool_to_load = str("halcmd setp pyvcp.first-tool %d" % tool)
                os.system(tool_to_load)

            set_z=True
        else:
           print(line.replace("\r", "").replace("\n", ""))

        match = re.match("(.*)G21(.*)", line)
        if match:
           #print("G21")
           print("O100 sub")
           print("  G49")
           print("  G54")
           print("  #<probe_height> = 19.32")
           print("  G0 Z25")
           print("  M108")
           print("  G38.2 Z-15 F140")
           print("  G10 L10 P#1 Z[#<probe_height>]")
           print("  G0 Z25")
           print("  G43")
           print("  M109")
           print("O100 endsub")
           print("M111")
           print("G28.1")
           print("M102")

        match = re.match("S(\d*)(.*)M3", line)
        if (match and is_on):
            speed = int(match.group(1))
            secs  = speed/1200
            print("G4 P%d" % secs)
            is_on = False
	  
        match = re.match("M5(.*)", line)
        if match:
            is_on= True

    tot_line_print = str("halcmd setp cpins.gcode_line_numbers %d" % tot_line_number)
    os.system(tot_line_print)

if __name__ == '__main__':
    main()

# vim:sw=4:sts=4:et:
