from PyTango import *
import time
f = open('homeXPositive.dmc', 'r')
prog = f.read()
con1 = DeviceProxy("p11/galildmc/eh.02")
con1.command_inout("Upload",str(prog))
start = con1.command_inout("StartUserTask1","HOMEX")
time.sleep(0.3)
print "Homing X"
while con1.read_attribute("UserTask1Running").value:
    time.sleep(0.1)
print "Done"
f = open('homeYPositive.dmc', 'r')
prog = f.read()
con1 = DeviceProxy("p11/galildmc/eh.02")
con1.command_inout("Upload",str(prog))
start = con1.command_inout("StartUserTask1","HOMEY")
time.sleep(0.3)
print "Homing Y"
while con1.read_attribute("UserTask1Running").value:
    time.sleep(0.1)
print "Done"
