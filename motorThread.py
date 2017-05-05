# -*- coding: utf-8 -*-
import sys
from PyTango import *
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import time
import string
import random
import thread
import os
from PyQt4.QtCore import SIGNAL, QThread
import ConfigParser
import random
import math
import Queue
from simulationDevice import SimulationDevice

class MotorThread(QThread):
    # A thread is started by calling QThread.start() never by calling run() directly!
    def __init__(self,deviceservers,onaxisZmountposition, gonioZmountposition):
        QThread.__init__(self)
        print "Motor  thread: Starting thread"
        self.simulation = 1
        self.debugMode = 0
        self.alive = False
        self.currentScanX = 0
        self.currentScanY = 0
        self.currentGonio = 0
        self.currentGonioZ = 0
        self.currentOnaxisX  = 0
        self.currentOnaxisY  = 0
        self.currentOnaxisZ  = 0
        self.currentBeamstopX  = 0
        self.currentBeamstopY  = 0
        self.stateTask1 = False
        
        self.stateProxyScanController = "OFF"
        self.stateProxyStepperController = "OFF"
        self.stateProxyScanX = "OFF"
        self.stateProxyScanY = "OFF"
        self.stateProxyGonio = "OFF"
        self.stateProxyGonioZ = "OFF"
        self.stateProxyOnaxisX = "OFF"
        self.stateProxyOnaxisY = "OFF"
        self.stateProxyOnaxisZ = "OFF"
        self.stateProxyBeamstopX = "OFF"
        self.stateProxyBeamstopY = "OFF"
        
        
        self.deviceservers = deviceservers
        
        self.onaxisZmountposition = float(onaxisZmountposition)
        self.gonioZmountposition = float(gonioZmountposition)
        self.prevOnaxisZposition = 0.0
        self.prevGonioZposition = 0.0
        
        self.inMountPosition = False
        
        if self.simulation:
            print "Motor thread in simulation mode"
            self.proxyScanController = SimulationDevice()
            self.proxyStepperController = SimulationDevice()
            self.proxyScanX = SimulationDevice()
            self.proxyScanY = SimulationDevice()
            self.proxyGonio = SimulationDevice()
            self.proxyGonioZ = SimulationDevice()
            self.proxyOnaxisX = SimulationDevice()
            self.proxyOnaxisY = SimulationDevice()
            self.proxyOnaxisZ = SimulationDevice()
            self.proxyBeamstopX = SimulationDevice()
            self.proxyBeamstopY = SimulationDevice()
            
            self.proxyScanX.write_attribute("VelocityUnits",1500)
            self.proxyScanY.write_attribute("VelocityUnits",1500)
            self.proxyGonio.write_attribute("VelocityUnits",1500)
            self.proxyGonioZ.write_attribute("VelocityUnits",1500)
            self.proxyOnaxisX.write_attribute("VelocityUnits",1500)
            self.proxyOnaxisY.write_attribute("VelocityUnits",1500)
            self.proxyOnaxisZ.write_attribute("VelocityUnits",1500)
            self.proxyBeamstopX.write_attribute("VelocityUnits",1500)
            self.proxyBeamstopY.write_attribute("VelocityUnits",1500)
            
            self.proxyScanX.write_attribute("SoftCwLimit",2000)
            self.proxyScanX.write_attribute("SoftCcwLimit",-2000)
            self.proxyScanY.write_attribute("SoftCwLimit",2000)
            self.proxyScanY.write_attribute("SoftCcwLimit",-2000)
             
            
        else:
            try:
                
                self.proxyScanController = DeviceProxy(self.deviceservers[0])
                self.proxyStepperController = DeviceProxy(self.deviceservers[1])
                self.proxyScanX = DeviceProxy(self.deviceservers[2])
                self.proxyScanY = DeviceProxy(self.deviceservers[3])
                self.proxyGonio = DeviceProxy(self.deviceservers[4])
                self.proxyGonioZ = DeviceProxy(self.deviceservers[5])
                self.proxyOnaxisX = DeviceProxy(self.deviceservers[6])
                self.proxyOnaxisY = DeviceProxy(self.deviceservers[7])
                self.proxyOnaxisZ = DeviceProxy(self.deviceservers[8])
                self.proxyBeamstopX = DeviceProxy(self.deviceservers[9])
                self.proxyBeamstopY = DeviceProxy(self.deviceservers[10])
                
                if self.proxyScanX.state() == DevState.OFF: self.proxyScanX.command_inout("Enable")
                if self.proxyScanY.state() == DevState.OFF: self.proxyScanY.command_inout("Enable")
                if self.proxyGonio.state() == DevState.OFF: self.proxyGonio.command_inout("Enable")
                if self.proxyGonioZ.state() == DevState.OFF: self.proxyGonioZ.command_inout("Enable")
                if self.proxyOnaxisX.state() == DevState.OFF: self.proxyOnaxisX.command_inout("Enable")
                if self.proxyOnaxisY.state() == DevState.OFF: self.proxyOnaxisY.command_inout("Enable")
                if self.proxyOnaxisZ.state() == DevState.OFF: self.proxyOnaxisZ.command_inout("Enable")
                if self.proxyBeamstopX.state() == DevState.OFF: self.proxyBeamstopX.command_inout("Enable")
                if self.proxyBeamstopY.state() == DevState.OFF: self.proxyBeamstopY.command_inout("Enable")
                
            except:
                self.alive = False
                self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
                raise
            
        print "Piezo thread: started"
        
        try:
            self.scanXMax = self.proxyScanX.read_attribute("SoftCwLimit").value
            self.scanXMin = self.proxyScanX.read_attribute("SoftCcwLimit").value
        except:
            self.scanXMax = self.proxyScanX.read_attribute("SoftCwLimit").value
            self.scanXMin = self.proxyScanX.read_attribute("SoftCcwLimit").value
            
        try:
            self.scanYMax = self.proxyScanY.read_attribute("SoftCwLimit").value
            self.scanYMin = self.proxyScanY.read_attribute("SoftCcwLimit").value
        except:
            self.scanYMax = self.proxyScanY.read_attribute("SoftCwLimit").value
            self.scanYMin = self.proxyScanY.read_attribute("SoftCcwLimit").value
        self.alive = True
        self.proxyScanController.command_inout("WriteRead","SDA=3000000")
        self.proxyScanController.command_inout("WriteRead","SDB=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDA=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDB=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDC=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDD=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDE=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDF=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDG=3000000")
        self.proxyStepperController.command_inout("WriteRead","SDH=3000000")
        self.proxyScanX.write_attribute("Velocity",1500)
        self.proxyScanY.write_attribute("Velocity",1500)
    def stop(self):
        print "Motor thread: Stopping thread"
        self.alive = False
        self.wait() # waits until run stops on his own

    def run(self):
        print "Motor thread: started"
        self.alive = True
        while self.alive:
            time.sleep(0.1)
            self.readAttributes()
            self.emit(SIGNAL("update()"))
        # exit position of run function of thread. if exiting == true we end up here
        self.valid = 0
        self.status = "OFFLINE"
        
        print "Motor thread: died"

    def join(self, timeout=None):
        print "Motor thread: join method"
        self.alive = False

    def readAttributes(self):
        try:
            self.stateProxyScanController = self.proxyScanController.state()
            self.stateProxyScanX = self.proxyScanX.state()
            self.stateProxyScanY = self.proxyScanY.state()
            self.stateProxyGonio = self.proxyGonio.state()
            self.stateProxyGonioZ = self.proxyGonioZ.state()
            self.stateProxyOnaxisX = self.proxyOnaxisX.state()
            self.stateProxyOnaxisY = self.proxyOnaxisY.state()
            self.stateProxyOnaxisZ = self.proxyOnaxisZ.state()
            self.stateProxyBeamstopX = self.proxyBeamstopX.state()
            self.stateProxyBeamstopY = self.proxyBeamstopY.state()
            
             
            self.currentScanX = self.proxyScanX.read_attribute("Position").value
            self.currentScanY = self.proxyScanY.read_attribute("Position").value
            self.currentGonio = self.proxyGonio.read_attribute("Position").value
            self.currentGonioZ = self.proxyGonioZ.read_attribute("Position").value
            self.currentOnaxisX  = self.proxyOnaxisX.read_attribute("Position").value
            self.currentOnaxisY  = self.proxyOnaxisY.read_attribute("Position").value
            self.currentOnaxisZ  = self.proxyOnaxisZ.read_attribute("Position").value
            self.currentBeamstopX  = self.proxyBeamstopX.read_attribute("Position").value
            self.currentBeamstopY  = self.proxyBeamstopY.read_attribute("Position").value
            self.stateTask1 = self.proxyScanController.read_attribute("UserTask1Running").value
            
        except:
            self.alive = False
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
 
    def uploadScript(self, arg):
        if self.debugMode: print "Motor thread: uploadScript(), arg:", arg
        try:
            self.proxyScanController.command_inout("Upload", arg)
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
        
    def startScript(self, arg):
        if self.debugMode: print "Motor thread: startScript(), arg:", arg
        try:
            self.proxyScanController.command_inout("StartUserTask1", arg)
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
   
    def isScriptRunning(self):
        if self.debugMode: print "Motor thread: isScriptRunning()"
        try:
            value = self.proxyScanController.read_attribute("UserTask1Running").value
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
        return bool(value)
    
    def checkBeamDump(self):
        if self.debugMode: print "Motor thread: checkBeamDump()"
        try:
            value = int(self.proxyScanController.command_inout("BEAMDPE=?"))
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
        return bool(value)
   
    def setScanX(self,arg):
        if self.debugMode: print "Motor thread: setScanX(), arg:", arg
        try:
            self.proxyScanX.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateScanX(self,arg):
        if self.debugMode: print "Motor thread: calibrateScanX(), arg:", arg
        try:
            self.proxyScanX.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    
    def setScanY(self,arg):
        if self.debugMode: print "Motor thread: setScanY(), arg:", arg
        try:
            self.proxyScanY.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateScanY(self,arg):
        if self.debugMode: print "Motor thread: calibrateScanY(), arg:", arg
        try:
            self.proxyScanY.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
            
    def setGonio(self,arg):
        if self.debugMode: print "Motor thread: setGonio(), arg:", arg
        try:
            self.proxyGonio.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateGonio(self,arg):
        if self.debugMode: print "Motor thread: calibrateGonio(), arg:", arg
        try:
            self.proxyGonio.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
                        
    def setGonioZ(self,arg):
        if self.debugMode: print "Motor thread: setGonioZ(), arg:", arg
        try:
            self.proxyGonioZ.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateGonioZ(self,arg):
        if self.debugMode: print "Motor thread: calibrateGonioZ(), arg:", arg
        try:
            self.proxyGonioZ.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
            
    def setOnaxisX(self,arg):
        if self.debugMode: print "Motor thread: setOnaxisX(), arg:", arg
        try:
            self.proxyOnaxisX.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateOnaxisX(self,arg):
        if self.debugMode: print "Motor thread: calibrateOnaxisX(), arg:", arg
        try:
            self.proxyOnaxisX.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])

    def setOnaxisY(self,arg):
        if self.debugMode: print "Motor thread: setOnaxisY(), arg:", arg
        try:
            self.proxyOnaxisY.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateOnaxisY(self,arg):
        if self.debugMode: print "Motor thread: calibrateOnaxisY(), arg:", arg
        try:
            self.proxyOnaxisY.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
            
    def setOnaxisZ(self,arg):
        if self.debugMode: print "Motor thread: setOnaxisZ(), arg:", arg
        try:
            self.proxyOnaxisZ.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateOnaxisZ(self,arg):
        if self.debugMode: print "Motor thread: calibrateOnaxisZ(), arg:", arg
        try:
            self.proxyOnaxisZ.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
            
    def setBeamstopX(self,arg):
        if self.debugMode: print "Motor thread: setBeamstopX(), arg:", arg
        try:
            self.proxyBeamstopX.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    def calibrateBeamstopX(self,arg):
        if self.debugMode: print "Motor thread: calibrateBeamstopX(), arg:", arg
        try:
            self.proxyBeamstopX.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])

    def setBeamstopY(self,arg):
        if self.debugMode: print "Motor thread: setBeamstopY(), arg:", arg
        try:
            self.proxyBeamstopY.write_attribute("Position", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])                                    
    def calibrateBeamstopY(self,arg):
        if self.debugMode: print "Motor thread: calibrateBeamstopY(), arg:", arg
        try:
            self.proxyBeamstopY.command_inout("Calibrate", arg)  
            
        except:
            self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
    
    def setMountPosition(self,arg):
        if self.debugMode: print "Motor thread: setOnaxisZoutposition(), arg:", arg
        if arg:
            try:
                self.prevOnaxisZposition = self.currentOnaxisZ
                self.proxyOnaxisZ.write_attribute("Position", self.onaxisZmountposition)
                self.prevGonioZposition = self.currentGonioZ
                self.proxyGonioZ.write_attribute("Position", self.gonioZmountposition)
                
                self.inMountPosition = True  
            
            except:
                print sys.exc_info()[1]
                self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
                
        else:
            try:
                self.proxyOnaxisZ.write_attribute("Position", self.prevOnaxisZposition)
                self.proxyGonioZ.write_attribute("Position", self.prevGonioZposition)
                self.inMountPosition = False  
            
            except:
                self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])      
        
    def stopMotors(self):
        if self.debugMode: print "Motor thread: stopMotors()"
        if self.proxyScanX.state() == DevState.MOVING: self.proxyScanX.command_inout("Stop")
        if self.proxyScanY.state() == DevState.MOVING: self.proxyScanY.command_inout("Stop")
        if self.proxyGonio.state() == DevState.MOVING: self.proxyGonio.command_inout("Stop")
        if self.proxyGonioZ.state() == DevState.MOVING: self.proxyGonioZ.command_inout("Stop")
        if self.proxyOnaxisX.state() == DevState.MOVING: self.proxyOnaxisX.command_inout("Stop")
        if self.proxyOnaxisY.state() == DevState.MOVING: self.proxyOnaxisY.command_inout("Stop")
        if self.proxyOnaxisZ.state() == DevState.MOVING: self.proxyOnaxisZ.command_inout("Stop")
        if self.proxyBeamstopX.state() == DevState.MOVING: self.proxyBeamstopX.command_inout("Stop")
        if self.proxyBeamstopY.state() == DevState.MOVING: self.proxyBeamstopY.command_inout("Stop")
            
        moving = True
        while moving:
            try:
                x = 0
                if self.proxyScanX.state() == DevState.MOVING: x+=1
                if self.proxyScanY.state() == DevState.MOVING: x+=1
                if self.proxyGonio.state() == DevState.MOVING: x+=1
                if self.proxyGonioZ.state() == DevState.MOVING: x+=1
                if self.proxyOnaxisX.state() == DevState.MOVING: x+=1
                if self.proxyOnaxisY.state() == DevState.MOVING: x+=1
                if self.proxyOnaxisZ.state() == DevState.MOVING: x+=1
                if self.proxyBeamstopX.state() == DevState.MOVING: x+=1
                if self.proxyBeamstopY.state() == DevState.MOVING: x+=1
            
                if x>0: moving = False
            except:
                moving = False
                self.emit(SIGNAL("errorSignal(PyQt_PyObject)"),sys.exc_info()[1])
            
            else:
                moving = False
  
