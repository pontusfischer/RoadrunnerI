# -*- coding: utf-8 -*-
import sys
import time
from PyTango import *
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, QThread
import Queue
import math
import os
import numpy
#
from scipy import ndimage
           
class LCLScollector(QThread):

    ERR_NO_ERROR = 0
    ERR_CANCELLED = 1
    ERR_TYPE_MISMATCH = 2
    ERR_VALUE_OUT_OF_RANGE = 3
    ERR_TIMEOUT = 4
    ERR_ALREADY_RUNNING = 8
    ERR_INTERLOCK_NOT_SET = 9
    ERR_MISALIGNED_BEAMSTOP = 10
    ERR_PIEZOMOTOR_OFFLINE = 11
    ERR_WAIT_CONDITION_TIMEOUT = 12
    
    ERR_MSGS = [ \
        "Success.", \
        "Canceled.", \
        "Wrong parameter type.", \
        "Parameter value out of range.", \
        "Timeout during start up procedure.", \
        "", \
        "", \
        "", \
        "LCLS collection is already running.", \
    ]

    # A thread is started by calling QThread.start() never by calling run() directly!
    def __init__(self, motorThread, simulation = False):
        QThread.__init__(self)
        #self.MainWindow = mainwindowPassing
        print "LCLS collection thread: Starting thread"
        self.emit(SIGNAL("logSignal(PyQt_PyObject)"),"Preparing LCLS collection...")
        self.alive = True
        self.waitConditionActive = False
        self.dataCollectionActive = False
        self.remainingTime = 0.0
        self.parameters = { 
            "scanPoints": [], \
            "angle": 0.0, \
            "freq": 120.0, \
            "acclPulses": 30.0, \
            "gonioStart": 0.0, \
            "gonioStop": 0.0, \
            "startRow": 0.0, \
            "stopRow": 0.0, \
        }
        self.conditionsList = { \
            "collectionStarted": False , \
            }
        
        self.motorThread = motorThread
        self.percentDone = 0
        self.currentRow = -1
        self.initialGonio = self.motorThread.currentGonio
        self.beamDumpOccurred =0
    
    def stop(self):
        print "LCLS collector thread: Stopping thread"
        self.alive = False
        self.motorThread.setGonio(self.initialGonio)
        self.wait() # waits until run stops on his own

    def join(self, timeout=None):
        print "LCLS collector thread: join method"
        self.alive = False

    def run(self):
        self.alive = True
        self.starttime = time.time()
        print "LCLS collector thread: started"
        
        
        #start data collection
        f = open('scan.dmc', 'r')
        template = f.read()
        f.close()
        self.percentDone = 0.0
        direction = -1
        
        rows = self.parameters["scanPoints"]
        rows = rows[self.parameters["startRow"]:self.parameters["stopRow"]]
        self.currentRow = self.parameters["startRow"]
        
        self.initialGonio = self.motorThread.currentGonio
        gonioAngles = numpy.linspace(self.parameters["gonioStart"], self.parameters["gonioStop"], len(rows))
        
        
        for row in rows:
            if not self.alive:
                self.percentDone = 0.0
                self.emit(SIGNAL("scanFinished()"))
                return
            num = len(row)
            self.currentRow += 1
            print "currentRow is now",self.currentRow
            self.motorThread.setGonio(gonioAngles[self.currentRow])
            time.sleep(0.1)
            while self.motorThread.stateProxyGonio == DevState.MOVING:
                time.sleep(0.1)
            direction *= -1
            if(direction > 0):
                startX = row[0].x()
                startY = row[0].y()
            elif(direction < 0):
                startX = row[-1].x()
                startY = row[-1].y()
            else:
                return
            
            script = template.format( \
                startX=startX, \
                startY=startY, \
                angle=self.parameters["angle"], \
                num=num, \
                dir=direction, \
                freq=self.parameters["freq"], \
                pulses=self.parameters["acclPulses"], \
            )
            self.motorThread.uploadScript(script)
            self.motorThread.startScript("SCAN")
            time.sleep(0.5)
            self.emit(SIGNAL("scanUpdate()"))
            while(self.motorThread.isScriptRunning()):
                if not self.alive:
                    self.percentDone = 0.0
                    self.emit(SIGNAL("scanFinished()"))
                    return
                time.sleep(0.25)
            self.percentDone += 100.0 / len(rows)
            self.beamDumpOccurred = self.motorThread.checkBeamDump()
            self.emit(SIGNAL("lineFinished()"))
            self.emit(SIGNAL("scanUpdate()"))

        #stop data collection
        self.dataCollectionActive = False
        self.emit(SIGNAL("scanFinished()"))
        print "LCLS collector thread: Thread for LCLS collector died"
        self.emit(SIGNAL("logSignal(PyQt_PyObject)"),"LCLS collection finished.")
        self.alive = False

    def setParameters(self, data):
        if(type(data) != dict):
            return self.ERR_TYPE_MISMATCH
        for key in data:
            self.parameters[key] = data[key]

    def setParameter(self, key, data):
        self.parameters[key] = data
