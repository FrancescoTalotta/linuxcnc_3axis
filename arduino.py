#!/usr/bin/python
import serial
import hal
import sys
import time

PORT = "/dev/ttyACM0"
ser = serial.Serial(PORT, 115200, timeout=15)

#Now we create the HAL component and its pins
## HAL_IN  arduino can read from linuxCNC
## HAL_OUT arduino can write to linuxCNC

c = hal.component("arduino")
c.newpin("spindle_rev",hal.HAL_BIT,hal.HAL_IN)
c.newpin("vacuum_pump",hal.HAL_BIT,hal.HAL_IN)
c.newpin("servo_tool",hal.HAL_BIT,hal.HAL_IN)
c.newpin("temperature",hal.HAL_FLOAT,hal.HAL_OUT)

time.sleep(1)
c.ready()

spindle_rev=c['spindle_rev']
vacuum_pump=c['vacuum_pump']
servo_tool =c['servo_tool']


spindle_rev_old=0
vacuum_pump_old=0
servo_tool_old=0
temperature_old=0

try:
  while 1:
    time.sleep(.01)
# Spindle REV 
    spindle_rev=c['spindle_rev']
    if spindle_rev!=spindle_rev_old:
       spindle_rev_old=spindle_rev
       if spindle_rev=='0':
          ser.write("F")
       elif spindle_rev=='1':
          ser.write("E")
# Vacuum Pump
    vacuum_pump=c['vacuum_pump']
    if vacuum_pump!=vacuum_pump_old:
       vacuum_pump_old=vacuum_pump
       if vacuum_pump=='0':
          ser.write("B")
       elif vacuum_pump=='1':
          ser.write("A")
# Servo Tool
    servo_tool=c['servo_tool']
    if servo_tool!=servo_tool_old:
       servo_tool_old=servo_tool
       if servo_tool=='0':
          ser.write("L")
       elif servo_tool=='1':
          ser.write("U")
# Temperature
    while ser.inWaiting():
       temp = ser.read(4)
       c['temperature']=temp

except KeyboardInterrupt:
    raise SystemExit 
