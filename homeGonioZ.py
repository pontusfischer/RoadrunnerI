from PyTango import *
import time
print "Homing GonioZ"
con1 = DeviceProxy("p11/galildmc/eh.04")
con1.command_inout("WriteRead","SDB=2000000")
dev = DeviceProxy("p11/motor/eh.t2.02")
if dev.state() == DevState.OFF: dev.command_inout("Enable")
dev.write_attribute("SoftLimitEnable",False)
dev.write_attribute("Position",100000)
time.sleep(0.5)
while dev.state() == DevState.MOVING:
    time.sleep(0.1)
print "CCW limit reached. Calibrating."
time.sleep(0.5)
dev.command_inout("Calibrate",10300)
print "Moving to 0"
dev.write_attribute("Position",0)
time.sleep(0.1)
while dev.state() == DevState.MOVING:
    time.sleep(0.1)
print "Enabling soft limits"
dev.write_attribute("SoftLimitEnable",True)
print "Gonio done"