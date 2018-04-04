#!/usr/bin/python
import serial
import hal
import sys
import time

PORT = "/dev/ttyACM0"
ser = serial.Serial(PORT, 115200, timeout=0)

#Now we create the HAL component and its pins
## HAL_IN  arduino can read from linuxCNC
## HAL_OUT arduino can write to linuxCNC
#
c = hal.component("arduino")
c.newpin("spindle_rev",hal.HAL_BIT,hal.HAL_IN)
c.newpin("vacuum_pump",hal.HAL_BIT,hal.HAL_IN)
c.newpin("servo_tool",hal.HAL_BIT,hal.HAL_IN)
c.newpin("probe_3d",hal.HAL_BIT,hal.HAL_IN)
#c.newpin("temperature",hal.HAL_FLOAT,hal.HAL_OUT)

time.sleep(1)
c.ready()

spindle_rev=c['spindle_rev']
vacuum_pump=c['vacuum_pump']
servo_tool =c['servo_tool']
probe_3d   =c['probe_3d']



spindle_rev_old='False'
vacuum_pump_old='False'
servo_tool_old='False'
probe_3d_old='False'
#temperature_old=0

try:
  while 1:
    time.sleep(.01)
# Spindle REV 
    spindle_rev=c['spindle_rev']
    if spindle_rev!=spindle_rev_old:
       spindle_rev_old=spindle_rev
       if spindle_rev==False:
          ser.write("F")
       elif spindle_rev==True:
          ser.write("E")
# Vacuum Pump
    vacuum_pump=c['vacuum_pump']
    if vacuum_pump!=vacuum_pump_old:
       vacuum_pump_old=vacuum_pump
       if vacuum_pump==False:
          ser.write("B")
       elif vacuum_pump==True:
          ser.write("A")
# Servo Tool
    servo_tool=c['servo_tool']
    if servo_tool!=servo_tool_old:
       servo_tool_old=servo_tool
       if servo_tool==False:
          ser.write("L")
       elif servo_tool==True:
          ser.write("U")
# 3D Probe
    probe_3d=c['probe_3d']
    if probe_3d!=probe_3d_old:
       probe_3d_old=probe_3d
       if probe_3d==False:
          ser.write("L")
       elif probe_3d==True:
          ser.write("I")
# Temperature
    #while ser.inWaiting():
       #temp = ser.read(5)
       #c['temperature']=float(temp)

except KeyboardInterrupt:
    raise SystemExit 
