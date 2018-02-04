#!/usr/bin/python
from __future__ import print_function

__author__ = 'hase'
"""
eagle2linuxcnc
Filter program to adapt Eagle milling-files to linuxcnc

Eagle milling files use G-odes and other conventions that LinuxCNC (2.5, 2.6) does not understand.
This filter can be used to read in the Eagle-generated file and provide LinuxCNC compatible output.

This program is free software.
No warranties are provided:
- use this program at your own risk.
- output generated by this program may or may not cause damage to your machine, the author can not be held responsible.

Redistribution of this program is granted under the condition that the authors copyright is retained intact.

Copyright 2015 by Hartmut "hase" Semken, hase@hase.net

This project started as a simple file filter to twiddle the GCodes created by Eagle (or maybe other programs)
into something that LinuxCNC would not reject with an error message.

It later evolved by incorporating probing the PCB surface and adjusting the Z-axis height to follow the surface.
 I (H. Semken) can not take credit for the Z-probing/adjusting part at all.

The Z-adjustment code is based on an idea published by Poul-Henning Kamp. at http://phk.freebsd.dk/CncPcb/index.html.
His idea was implemented in Python by mattvenn
https://github.com/mattvenn/cad/blob/master/tools/etchZAdjust/Etch_Z_adjust.2.2.py

If you are looking for an interactive tool to do the Z-adjustment, just get mattvens version.
It works very well!
His code is not very "pythonic", so I rewrote some of his work, but that was only done to please myself, not out of necessity.

I took the code from mattven, stripped off the GUI, rewrote the parsing of etch moves and added my
(older, original) pattern-matching-replacing code.

The input file is parsed twice here, so it can not be a stream or from a pipe
In the first pass, the dimension of the PCB in X and Y are calculated and a probing grid is calculated.

In the second pass, the file is read line-by-line.

first, a header is output containing the GCode subroutines for probing the surface and doing the actual milling moves.
Then, each line is either
- copied to output unmodified (governed by variable passthrough, a list of regular expressions) or
- replaced by a fixed string (governed by variable zmod, a single regular expression) or
- skipped/ignored (governed by variable remove, a list of regular expressions)
- replaced by a fixed string (governed by variable replace, a list of (regex,replacement) tuples)
- replaced by a subroutine call doing an etch move (governed by variable etch, a regex)
- copied to output if no pattern matched

finally a footer is appended.

Except for the double parsing of the input file, the program acts as a filter: input->output.
In LinuxCNC it is possible to configure file types and this program is intended to be used there,
but of course you can simply redirect output to a file.

V 0.1: experimental, Feb 2015
- no imperial units, metric only.
- first attempt at incorporating Z-probing in filter-like fashion
- NO WARNINGS/CHECKS: even the most improbable input values are accepted!
- assumes *all* G01 in input are milling moves (or Z plunge) and G00 are non-milling moves
- does NOT handle drilling
- does NOT handle tool changes

"""

import sys, os

BASE = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), ".."))
sys.path.insert(0, os.path.join(BASE, "lib", "python"))

import re

# patterns governing the processing of input lines

# lines matching the passthrough pattern are copeid to output and not changed at all
passthrough = []

# lines matching the zmod pattern are changed;
# Eagle G-Code moves Z up as much as down; the up move is therefore usually too small, hence we fiddle with it.
zmod = "G00 Z\d"

# Lines matching any of these patterns are simply removed from the output
remove = ["%", "M48", "M71", "T\d\d", "G36 T \d", "G01.*Z-\d"]
# please note: the G01.*Z-\d does indeed remove all downward Z moves; the hights-adjusted milling subroutine
# does its own downward Z moves, therefore they are superflous

# replacement patterns: replace the line from the input with something else
# each element of the list is a tuple (pattern,replacement) of a regex to match and the string to replace it
# currently this only does simple replacements without parsing any values
replace = []

# constants to configure the probing
grid_clearance = 0.01  # added to the X-Y-outline on each side, so we probe slightly outside the milled area
probe_speed = 110.00  # speed for the probing downward move
z_safety = 3.00  # height over surface for rapid moves; surface = 0
z_probe = -0.5  # maximum depth for probing move
z_probe_detach = 20.00  # z height for tool changes/probe detachment

# distance between probe points; a 10mm grid works quite well for my machine using my homebrew vacuum table and
# pretty cheap PCB material.
# if you mechanically clamp the material, it will bend more and you will need more accuracy, e.g. a finer grid.
# increase (e.g. 20) if your PCB surfaces are very flat; Z-adjustment will be not as accurate but probing will be faster
# decrease to get better accuracy for the Z-adjustment at the cost of longer probing times.
# LinuxCNC is rumored to be able to handle up to 4000 probe points
step_size = 5

# constants to configure the milling moves

etch_speed = 220.00  # speed for the milling moves in machine units per minute
etch_depth = -0.05  # milling depth. PCB copper surface is Z=0, so set a negative value for actual milling, positive for dry runs
z_trivial = 0.05  # if the interpolation creates a z-move smaller than this, the move is ignored.

def progress(a, b):
    if os.environ.has_key("AXIS_PROGRESS_BAR"):
        print >> sys.stderr, "FILTER_PROGRESS=%d" % int(a * 100. / b + .5)
        sys.stderr.flush()


def main():

    # variables used in processing the input
    # dimensions of the board; will be recalculated from the input file
    XMin = 10000
    XMax = -10000
    YMin = 10000
    YMax = -10000

    infile = sys.argv[1]
    f = open(infile, "r")

    # first pass: parse the file, find the maxima in X and Y
    for line in f:
        # Quick explanation of the regular expression used here, since people asked :-)
        # the line is matched against the pattern in the string
        # re.match() returns None if the pattern did not match; None is false so the if can immediately test if we found a match
        # the pattern requires
        # - a capital G
        # - followed by one digit \d
        # - followed by any character (the dot is "any char") repeated zero or more times (* is "repeat")
        # - followed by an X
        # - followed by zero or more minus-signs -*
        # - followed by zero or more digits \d*
        # - followed by zero or more dots (. is "any" \. is "a dot") \.*
        # - followed by zero or more digits
        # phew!
        # the parenthesis capture the sub-string that matched in that position so we can refer to it as match.group(2)
        match = re.match("G(\d.*)X(-*\d*\.*\d*)", line)
        if match:  # we found an X value
            #debug output, if you want to experiment with the regex
            #print(match.group(0))
            #print(match.group(1))
            #print(match.group(2))
            val = float(match.group(2))
            XMin = min(XMin, val)
            XMax = max(XMax, val)
        # repeat regex-magic for an Y value
        match = re.match("G(\d.*)Y(-*\d*\.*\d*)", line)
        if match:  # we found an Y value
            #debug output, if you want to experiment with the regex
            #print(match.group(0))
            #print(match.group(1))
            #print(match.group(2))
            val = float(match.group(2))
            YMin = min(YMin, val)
            YMax = max(YMax, val)
    # now we know the dimension of the board and can create teh probing grid
    XSize = XMax - XMin
    YSize = YMax - YMin
    print("(board dimensions: XMin: %s, YMin: %s, XMax: %s, YMax: %s, XSize: %s YSize: %s)" % (XMin, YMin, XMax, YMax, XSize, YSize))

    # make the probing grid slightly larger than the actual board
    XMin = XMin - grid_clearance
    XMax = XMax + grid_clearance
    YMin = YMin - grid_clearance
    YMax = YMax + grid_clearance

    X_grid_lines = 2 + int(XSize / step_size)
    Y_grid_lines = 2 + int(YSize / step_size)

    # Make sure grid lines are at least 2
    if X_grid_lines < 2: X_grid_lines = 2
    if Y_grid_lines < 2: Y_grid_lines = 2

    # Now work out exact step sizes for X and Y
    Y_step_size = YSize / (Y_grid_lines - 1)
    X_step_size = XSize / (X_grid_lines - 1)

    print("(Probing grid, rows: %s, columns: %s, steps: %s, %s)" % (
        X_grid_lines, Y_grid_lines, X_step_size, Y_step_size))

    # lets start writing the output; header goes first

    print("(Z-compensated version of %s follows)" % (infile), end="\n")
    print("(the following parameters may be changed)")
    print("M5 (tunr off the spindle)")
    print("G21 (mm is machine unit; make sure to adjust other parameters accordingly if you change this)")

    print("#<_etch_depth>    =    %.4f \n" % (etch_depth), end="")
    print("#<_etch_speed>    =    %.4f \n" % (etch_speed), end="")
    print("#<_probe_speed>   =    %.4f \n" % (probe_speed), end="")
    print("#<_z_safety>      =    %.4f \n" % (z_safety), end="")
    print("#<_z_probe>       =    %.4f \n" % (z_probe), end="")
    print("#<_z_trivial>     =    %.4f \n\n" % (z_trivial), end="")

    print("(parameters calculated from the board size, do not change these manually)")
    print('#<_x_grid_origin> =    %.4f \n' % (XMin), end="")
    print('#<_x_grid_lines>  =    %.4f \n' % (X_grid_lines ), end="")
    print('#<_y_grid_origin> =    %.4f \n' % (YMin), end="")
    print('#<_y_grid_lines>  =    %.4f \n' % (Y_grid_lines ), end="")
    print('#<_x_step_size>   =    %.4f \n' % (X_step_size), end="")
    print('#<_y_step_size>   =    %.4f \n' % (Y_step_size), end="")
    print("#<_last_z_etch>   =    #<_etch_depth>", end="")

    print("""
(subroutines used for probing and for milling moves:)
O100 sub (probe subroutine)
     G00 X [#<_x_grid_origin> + #<_x_step_size>*#<_grid_x>]
     G38.2 Z#<_z_probe> F#<_probe_speed>
     #[1000 + #<_grid_x> + #<_grid_y> * #<_x_grid_lines>] = #5063
     G00 Z#<_z_safety>
O100 endsub

O200 sub (etch subroutine)
     ( This subroutine calculates way points on the way to x_dest, y_dest, )
     ( and calculates the Z adjustment at each way point.                  )
     ( It moves to each way point using the etch level and etch speed set  )
     ( in the configuration section above.                                 )

     #<x_start>         = #1
     #<y_start>         = #2
     #<x_dest>          = #3
     #<y_dest>          = #4
     #<distance>        = sqrt[ [#<x_dest> - #<x_start>]**2 + [#<y_dest> - #<y_start>]**2 ]
     #<waypoint_number> = fix[#<distance> / [#<_x_step_size>/2]]
     #<x_step>          = [[#<x_dest> - #<x_start>] / [#<waypoint_number> + 1]]
     #<y_step>          = [[#<y_dest> - #<y_start>] / [#<waypoint_number> + 1]]

     O201 while [#<waypoint_number> ge 0]
          #<_x_way>     =  [#<x_dest> - #<waypoint_number> * #<x_step>]
          #<_y_way>     =  [#<y_dest> - #<waypoint_number> * #<y_step>]
          #<_grid_x_w>  =  [[#<_x_way> - #<_x_grid_origin>]/#<_x_step_size>]
          #<_grid_y_w>  =  [[#<_y_way> - #<_y_grid_origin>]/#<_y_step_size>]
          #<_grid_x_0>  =  fix[#<_grid_x_w>]
          #<_grid_y_0>  =  fix[#<_grid_y_w>]
          #<_grid_x_1>  =  fup[#<_grid_x_w>]
          #<_grid_y_1>  =  fup[#<_grid_y_w>]
          #<_cell_x_w>  =  [#<_grid_x_w> - #<_grid_x_0>]
          #<_cell_y_w>  =  [#<_grid_y_w> - #<_grid_y_0>]

          (Bilinear interpolation equations from http://en.wikipedia.org/wiki/Bilinear_interpolation)
          #<F00>        =  #[1000 + #<_grid_x_0> + #<_grid_y_0> * #<_x_grid_lines>]
          #<F01>        =  #[1000 + #<_grid_x_0> + #<_grid_y_1> * #<_x_grid_lines>]
          #<F10>        =  #[1000 + #<_grid_x_1> + #<_grid_y_0> * #<_x_grid_lines>]
          #<F11>        =  #[1000 + #<_grid_x_1> + #<_grid_y_1> * #<_x_grid_lines>]
          #<b1>         =  #<F00>
          #<b2>         =  [#<F10> - #<F00>]
          #<b3>         =  [#<F01> - #<F00>]
          #<b4>         =  [#<F00> - #<F10> - #<F01> + #<F11>]
          #<z_adj>      =  [#<b1> + #<b2>*#<_cell_x_w> + #<b3>*#<_cell_y_w> + #<b4>*#<_cell_x_w>*#<_cell_y_w>]
          #<z_etch>     =  [#<_etch_depth> + #<z_adj>]

          (ignore trivial z axis moves)
          O202 if [abs[#<z_etch> - #<_last_z_etch> ] lt #<_z_trivial>]
               #<z_etch> = #<_last_z_etch>
          O202 else
               #<_last_z_etch> = #<z_etch>
          O202 endif

          (now do the move)
          G01 X#<_x_way>  Y#<_y_way>  Z[#<z_etch>] F[#<_etch_speed>]

          (and then go to the next way point)
          #<waypoint_number> = [#<waypoint_number> - 1]
     O201 endwhile
O200 endsub

( Probe grid section                                                                )
( This section probes the grid and writes the probe results for each probed point   )
( to variables #1000, #1001, #1002 etc etc such that the result at grid_x, grid_y   )
( on the grid is stored in memory location #[1000 + grid_x + grid_y*[x_grid_lines]] )
( EMC2 will run out of memory if you probe more than 4,000 points.                  )

#<_grid_x> = 0
#<_grid_y> = 0
G00 Z#<_z_safety>
G00 X#<_x_grid_origin> Y#<_y_grid_origin>
O001 while [#<_grid_y> lt #<_y_grid_lines>]
 G00 Y[#<_y_grid_origin> + #<_y_step_size> * #<_grid_y>]
 O002 if [[#<_grid_y> / 2] - fix[#<_grid_y> / 2] eq 0]
      #<_grid_x> = 0
      O003 while [#<_grid_x> lt #<_x_grid_lines>]
           O100 call (probe subroutine)
           #<_grid_x> = [#<_grid_x> + 1]
      O003 endwhile
 O002 else
      #<_grid_x> = #<_x_grid_lines>
      O004 while [#<_grid_x> gt 0]
           #<_grid_x> = [#<_grid_x> - 1]
           O100 call (probe subroutine)
      O004 endwhile
 O002 endif
 #<_grid_y> = [#<_grid_y> + 1]
O001 endwhile
""", end="")
    print("G00 Z%.4f \n" % (z_probe_detach), end="")
    print("""
( Main G code section                                                               )
( The filter has replaced all G01 etch moves from original file eg G01 Xaa Ybb Zcc Fdd  )
( with an adjusted etch move in the format: O200 sub [x_start] [y_start] [aa] [bb]  )
( O200 is the etch subroutine                                                       )

(MSG, remove Probe, insert tool, prepare for milling)

M00
S20000
M3

""", end="")
    f.close()
    # initialize coordinate variables
    X_dest = XMin
    Y_dest = YMin
    Z_dest = z_safety
    X_start = X_dest
    Y_start = Y_dest
    Z_start = Z_dest

    f = open(infile, "r")  # open the file again for the second pass
    # and process line by line
    for line in f:
        # first pattern match: passthrough
        passed = False
        for pattern in passthrough:
            match = re.match(pattern, line)
            if match:  # we found a match
                passed = True  # remember that we have processed the line and can skip all other matching
                print(line, end="")  # output the line
                break  # stop processing the passthrough patterns
        if passed:  # if we have processed the line
            passed = False
            continue  # continue the for line in f loop: process the next line

        # next check: upward Z moves
        match = re.match(zmod, line)
        if match:
            zmove = "G00 Z%s" % z_safety
            print(zmove, end="\n")  # output our Z-up move, replacing the one from the input
            continue  # skip to the next line in the input file

        # next: lines to be deleted; very similar to passthrough, just without any output :-)
        for pattern in remove:
            passed = False
            match = re.match(pattern, line)
            if match:  # remove pattern was found
                passed = True
                break  # breaks the loop searching for remove patterns
        if passed:
            passed = False
            continue  # read next line

        for (pattern, rep) in replace:
            passed = False
            match = re.match(pattern, line)
            if match:
                passed = True
                print(rep, end="") # output the replacement for the pattern
                break
        if passed:
            passed = False
            continue  # next line from file

        # now we parse the remaining input and replace milling moves by subroutine calls
        # the rapid moves stay unchanged, but we need to record the coordinates: the end of such a rapid is start
        # of the next milling move

        # start coordinates for the current move are the end coordinates of the previous move
        X_start = X_dest
        Y_start = Y_dest
        Z_start = Z_dest

        # find out the type of move we have (G00 or G01)
        match = re.match("G(\d*)",line)
        if match:
            Gval = int(match.group(1))

        # extract the X coordinate from the line
        match = re.match(".*X(-*\d*\.*\d*)",line)
        if match:
            X_dest = float(match.group(1))

        # and also the Y coordinate
        match = re.match(".*Y(-*\d*\.*\d*)",line)
        if match:
            Y_dest = float(match.group(1))

        # if the move as a milling move (G01), replace it with a subroutine call
        if Gval == 1:
            print('O200 call [%.4f] [%.4f] [%.4f] [%.4f]\n' % (X_start, Y_start, X_dest, Y_dest),end="")
        # anything that is not a G1/G01 is simply copied to output
        else:
            print(line)
    print("M5 (spindle off)")
    print("M30 (Program End)")

if __name__ == '__main__':
    main()

# vim:sw=4:sts=4:et:
