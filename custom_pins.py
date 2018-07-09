#!/usr/bin/python
import hal
import sys
import time

#Now we create the HAL component and its pins

d = hal.component("cpins")

d.newpin("gcode_line_numbers",hal.HAL_U32,hal.HAL_IN)
d.newpin("gcode_current_line_number",hal.HAL_S32,hal.HAL_IN)
d.newpin("gcode_percent",hal.HAL_U32,hal.HAL_OUT)

time.sleep(1)
d.ready()

gcode_line_numbers_old=0
gcode_current_line_number_old=0
gcode_percent=0

gcode_line_numbers=d['gcode_line_numbers']
gcode_current_line_number=d['gcode_current_line_number']


try:
  while 1:
    time.sleep(.1)
# g-code percent estimation
    gcode_line_numbers        = d['gcode_line_numbers']
    gcode_current_line_number = d['gcode_current_line_number']
    if gcode_current_line_number!=gcode_current_line_number_old:
       gcode_current_line_number_old=gcode_current_line_number
       if gcode_line_numbers!=0:
          code_percent = (float(gcode_current_line_number)/float(gcode_line_numbers))*100
       if gcode_line_numbers==0:
          code_percent = 0 
       if code_percent > 100:
          code_percent = 100
       d['gcode_percent'] = int(code_percent)

except KeyboardInterrupt:
    raise SystemExit 
