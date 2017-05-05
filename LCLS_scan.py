#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
@author: pontusfr
'''
import sys
from PyQt4 import QtCore, QtGui, QtOpenGL
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from LCLSGUI import Ui_pyLCLS
import time
import string
import random
import os
from PyQt4.QtCore import SIGNAL, QThread
import ConfigParser
from PyQt4.QtCore import Qt, QTimer
import csv
import numpy
from mjpgStream import MjpgStream
import math
from copy import deepcopy
from Raster import Raster, RasterItem
from motorThread import MotorThread
from numpy import arctan
from dataCollectionThread import LCLScollector
from filesystem import Filesystem
from autofocus import AutoFocus
from PyTango import *
import cPickle as pickle
class StartQT4(QtGui.QMainWindow):

    #cameraServer = "haspp11mobile"
    cameraServer = "haspp11exp03"
    cameraPort = 8088
    camera = None
    cameraImageItem = None
    raster = None
    rasterItem = None
    rasterGroup = None
    draggingRaster = None
    lastDraggingRaster = None
    dragging = False
    rotating = False
    
    definingTopLeft = False
    definingTopRight = False
    definingBottomLeft = False
    allCornersDefined = False
    topLeftPos = None
    topRightPos = None
    bottomLeftPos = None
    
    topLeftEllipseItem = None
    topRightEllipseItem = None
    bottomLeftEllipseItem = None
    bottomRightEllipseItem = None
    
    orthoLineItem = None
    abLineItem = None
    assistLine = None
    assistLineItem = None
    ellipseItem = None
    cornerOrthoLinesRemoved = False
    
    LCLScollector = None
    filesystem = None
    autofocus = None
    beamoffsetX = 0
    beamoffsetY = 0
    settingBeamPosition = False
    topLeftCoarse = (0,0)
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_pyLCLS()
        self.ui.setupUi(self)
        self.connect(self, QtCore.SIGNAL('triggered()'), self.closeEvent)
        
        
        
        self.filesystem = Filesystem()
        self.filesystem.setSample("blupp")
        print "Filesystem path:",self.filesystem.getPath(self.filesystem.FS_ROOT_LOCAL+self.filesystem.FS_SUB_PROCESSED+self.filesystem.FS_TYPE_SCAN)
        self.raster = RasterItem()
        
        

        self.connectCamera()
        
        #self.virtualWidth=3*851.0*(1800.0/(851.0/self.raster.conversion.getValue()))
        #self.virtualHeight=3*638.0*(1800.0/(638.0/self.raster.conversion.getValue()))
        self.virtualWidth=12000
        self.virtualHeight=12000
        #print "virtualHeight",self.virtualHeight,"virtualWidth",self.virtualWidth
        self.sceneLiveview = QtGui.QGraphicsScene(self)
        self.sceneDims = QtCore.QRectF(-self.virtualWidth/2,-self.virtualHeight/2,self.virtualWidth,self.virtualHeight)
        
        
        #self.raster.raster.setOffset(self.virtualWidth/2,self.virtualHeight/2)
        
        
        #self.raster.raster.setPixmapSize(0.0, 0.0)
        self.raster.raster.setPixmapSize(12000, 12000)
        self.raster.beamsize.setValue(QtCore.QPointF(10.0, 10.0))
        self.raster.stepsize.setValue(QtCore.QPointF(13.0, 13.0))

        self.raster.conversion.setValue(2.182)
        self.raster.raster.setOffset(0,000)
        self.raster.scanType.setValue(Raster.RASTER_SCAN_TRIANGULAR)
        
        self.ui.doubleSpinBoxPixelsPerUm.setValue(self.raster.conversion.getValue())
        
        #self.ellipseWidth = 10*1.55
        #self.ellipseHeight = 10*1.55
        self.ellipseX = 0
        self.ellipseY = 0
        self.centreX = 0
        self.centreY = 0
        
        #print "sceneDims",-self.virtualWidth/2,-self.virtualHeight/2,self.virtualWidth,self.virtualHeight
        
        self.sceneLiveview.setSceneRect(self.sceneDims)
        
        
        self.sceneLiveview.addItem(self.raster)
        self.ui.graphicsviewLiveview.setScene(self.sceneLiveview)
        self.ui.graphicsviewLiveview.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsviewLiveview.setInteractive(True)
        #self.ui.graphicsviewLiveview.setMouseTracking(True)
        self.ui.graphicsviewLiveview.update()
        self.installEventFilter(self)
        self.sceneLiveview.installEventFilter(self)
        
        QtCore.QObject.connect(self.ui.doubleSpinBoxAngle,QtCore.SIGNAL("editingFinished()"), self.setRasterAngle)
        QtCore.QObject.connect(self.raster.angle,QtCore.SIGNAL("valueEdited(double)"), self.ui.doubleSpinBoxAngle.setValue)
        QtCore.QObject.connect(self.ui.doubleSpinBoxYZpitch,QtCore.SIGNAL("valueChanged(double)"), self.setYZpitch)
        
        
        QtCore.QObject.connect(self.ui.doubleSpinBoxBeamsize,QtCore.SIGNAL("valueChanged(double)"), self.setBeamsize)
        QtCore.QObject.connect(self.ui.pushButtonClearRaster,QtCore.SIGNAL("clicked()"), self.clearRaster)
        QtCore.QObject.connect(self.ui.pushButtonAutofocusGonioZ,QtCore.SIGNAL("clicked()"), self.autoFocusGonioZ)
        QtCore.QObject.connect(self.ui.pushButtonAutofocusGonio,QtCore.SIGNAL("clicked()"), self.autoFocusGonio)
        QtCore.QObject.connect(self.ui.checkBoxAutoExposure, QtCore.SIGNAL("stateChanged(int)"), self.setAutoExposure)
        QtCore.QObject.connect(self.ui.checkBoxAutoGain, QtCore.SIGNAL("stateChanged(int)"), self.setAutoGain)
        
        QtCore.QObject.connect(self.ui.pushButtonSaveImage,QtCore.SIGNAL("clicked()"), self.SaveImage)
        QtCore.QObject.connect(self.ui.pushButtonSetBeamPosition,QtCore.SIGNAL("clicked()"), self.setBeamPosition)
            
        QtCore.QObject.connect(self.ui.pushButtonSetTopLeft,QtCore.SIGNAL("clicked()"), self.setTopLeft)
        QtCore.QObject.connect(self.ui.pushButtonSetTopRight,QtCore.SIGNAL("clicked()"), self.setTopRight)
        QtCore.QObject.connect(self.ui.pushButtonSetBottomLeft,QtCore.SIGNAL("clicked()"), self.setBottomLeft)
        QtCore.QObject.connect(self.ui.pushButtonStopAll,QtCore.SIGNAL("clicked()"), self.stopAll)
        QtCore.QObject.connect(self.ui.pushButtonStopAll2,QtCore.SIGNAL("clicked()"), self.stopAll)
        
        QtCore.QObject.connect(self.ui.pushButtonUp,QtCore.SIGNAL("clicked()"), self.moveUp)
        QtCore.QObject.connect(self.ui.pushButtonDown,QtCore.SIGNAL("clicked()"), self.moveDown)
        QtCore.QObject.connect(self.ui.pushButtonLeft,QtCore.SIGNAL("clicked()"), self.moveLeft)
        QtCore.QObject.connect(self.ui.pushButtonRight,QtCore.SIGNAL("clicked()"), self.moveRight)
        QtCore.QObject.connect(self.ui.pushButtonResetMotors,QtCore.SIGNAL("clicked()"), self.moveZero)
        
        QtCore.QObject.connect(self.ui.pushButtonSetTopLeftCoarse,QtCore.SIGNAL("clicked()"), self.setTopLeftCoarse)
        QtCore.QObject.connect(self.ui.pushButtonMoveTopLeft,QtCore.SIGNAL("clicked()"), self.moveTopLeft)
        QtCore.QObject.connect(self.ui.pushButtonMoveTopRight,QtCore.SIGNAL("clicked()"), self.moveTopRight)
        QtCore.QObject.connect(self.ui.pushButtonMoveBottomRight,QtCore.SIGNAL("clicked()"), self.moveBottomRight)
        QtCore.QObject.connect(self.ui.pushButtonMoveBottomLeft,QtCore.SIGNAL("clicked()"), self.moveBottomLeft)
        QtCore.QObject.connect(self.ui.pushButtonMoveCentre,QtCore.SIGNAL("clicked()"), self.moveCentre)
        
        
        
        QtCore.QObject.connect(self.ui.pushButtonSetMountPosition,QtCore.SIGNAL("clicked()"), self.setMountPosition)
        QtCore.QObject.connect(self.ui.comboBoxStepSize,QtCore.SIGNAL("activated(int)"), self.setStepSize)
        QtCore.QObject.connect(self.ui.comboBoxStepSize_2,QtCore.SIGNAL("activated(int)"), self.setStepSize2)
        
        QtCore.QObject.connect(self.ui.pushButtonGoRowHole,QtCore.SIGNAL("clicked()"), self.goToRowHole)
        
        
        QtCore.QObject.connect(self.ui.pushButtonStartScan,QtCore.SIGNAL("clicked()"), self.startScan)
        QtCore.QObject.connect(self.ui.pushButtonAbortScan,QtCore.SIGNAL("clicked()"), self.abortScan)
        
        
        self.ui.pushButtonSetTopLeft.setEnabled(True)
        self.ui.pushButtonSetTopRight.setEnabled(False)
        self.ui.pushButtonSetBottomLeft.setEnabled(False)

        self.loadSettings()
        self.setHolePitch() 
        #QTimer.singleShot(2000, self.doGrid)
    def closeEvent(self, *args, **kwargs):
        self.saveSettings()
        return QtGui.QMainWindow.closeEvent(self, *args, **kwargs)
    def loadSettings(self):
        print "Trying to open settings file"
        self.settingsFile = os.path.realpath(os.path.dirname(sys.argv[0])) + '/' + "settings.cfg"
        if os.path.isfile(self.settingsFile):
            print "Loading settings"
            config = ConfigParser.ConfigParser()
            config.read(self.settingsFile)
            self.beamtimeID = config.get('ISMOscan', 'beamtime')
            motorScanController = config.get('ISMOscan', 'scancontroller')
            motorStepperController = config.get('ISMOscan', 'steppercontroller')
            motorScanXDevname = config.get('ISMOscan', 'scanx')
            motorScanYDevname = config.get('ISMOscan', 'scany')
            motorGonioDevname = config.get('ISMOscan', 'gonio')
            motorGonioZDevname = config.get('ISMOscan', 'gonioz')
            motorOnaxisXDevname = config.get('ISMOscan', 'onaxisx')
            motorOnaxisYDevname = config.get('ISMOscan', 'onaxisy')
            motorOnaxisZDevname = config.get('ISMOscan', 'onaxisz')
            self.focusDevice = motorGonioZDevname
            self.focusDevice2 = motorGonioDevname
            motorBeamstopXDevname = config.get('ISMOscan', 'beamstopx')
            motorBeamstopYDevname = config.get('ISMOscan', 'beamstopy')
            onaxisZmountposition = config.get('ISMOscan', 'onaxisZmountposition')
            gonioZmountposition = config.get('ISMOscan', 'gonioZmountposition')
            self.cameraServer = config.get('Camera', 'cameraserver')
            self.cameraPort = int(config.get('Camera', 'cameraport'))
            
            
            motorServers = [motorScanController, motorStepperController, motorScanXDevname, \
                            motorScanYDevname, motorGonioDevname,motorGonioZDevname, \
                            motorOnaxisXDevname, motorOnaxisYDevname, motorOnaxisZDevname, \
                            motorBeamstopXDevname, motorBeamstopYDevname]
            
            self.motorThread = MotorThread(motorServers,onaxisZmountposition,gonioZmountposition)
            self.connect(self.motorThread,SIGNAL("update()"),self.updatePositions)
            self.motorThread.start()
            time.sleep(0.5)
            self.ui.horizontalSliderXPosition.setMinimum(int(self.motorThread.scanXMin))
            self.ui.horizontalSliderXPosition.setMaximum(int(self.motorThread.scanXMax))
            self.ui.horizontalSliderXPosition.setValue(int(self.motorThread.currentScanX))
            
            self.ui.verticalSliderYPosition.setMinimum(int(self.motorThread.scanYMin))
            self.ui.verticalSliderYPosition.setMaximum(int(self.motorThread.scanYMax))
            self.ui.verticalSliderYPosition.setValue(int(self.motorThread.currentScanY))
            
            self.ui.doubleSpinBoxScanXposition.setValue(self.motorThread.currentScanX)
            self.ui.doubleSpinBoxScanYposition.setValue(self.motorThread.currentScanY)
            self.ui.doubleSpinBoxGonioAngle.setValue(self.motorThread.currentGonio)
            self.ui.doubleSpinBoxGonioAngle_2.setValue(self.motorThread.currentGonio)
            
            self.ui.doubleSpinBoxGonioZposition.setValue(self.motorThread.currentGonioZ)
            self.ui.doubleSpinBoxOnaxisXposition.setValue(self.motorThread.currentOnaxisX)
            self.ui.doubleSpinBoxOnaxisYposition.setValue(self.motorThread.currentOnaxisY)
            self.ui.doubleSpinBoxOnaxisZposition.setValue(self.motorThread.currentOnaxisZ)
            self.ui.doubleSpinBoxBeamstopXposition.setValue(self.motorThread.currentBeamstopX)
            self.ui.doubleSpinBoxBeamstopYposition.setValue(self.motorThread.currentBeamstopY)
            
            
            #load saved settings
            pixelsPerUm = float(config.get('SavedSettings', 'scale'))
            holePitch = float(config.get('SavedSettings', 'holepitch'))
            gridAngle = float(config.get('SavedSettings', 'gridangle'))
            YZpitch = float(config.get('SavedSettings', 'yzpitch'))
            beamSize = float(config.get('SavedSettings', 'beamsize'))
            beamx = float(config.get('SavedSettings', 'beamx'))
            beamy = float(config.get('SavedSettings', 'beamy'))
            scanName = str(config.get('SavedSettings', 'scanname'))
            angleIncStart = float(config.get('SavedSettings', 'angleincstart'))
            angleIncStop = float(config.get('SavedSettings', 'angleincstop'))
            startrow = int(config.get('SavedSettings', 'startrow'))
            stoprow = int(config.get('SavedSettings', 'stoprow'))
            frequency = int(config.get('SavedSettings', 'frequency'))
            accPulses = int(config.get('SavedSettings', 'accpulses'))

            
            self.ui.doubleSpinBoxPixelsPerUm.setValue(pixelsPerUm)
            self.ui.doubleSpinBoxHolePitch.setValue(holePitch)
            self.ui.doubleSpinBoxAngle.setValue(gridAngle)
            self.ui.doubleSpinBoxYZpitch.setValue(YZpitch)
            self.ui.doubleSpinBoxBeamsize.setValue(beamSize)
            self.ui.spinBoxBeamX.setValue(beamx)
            self.ui.spinBoxBeamY.setValue(beamy)
            self.ui.lineEditScanName.setText(scanName)
            self.ui.doubleSpinBoxStartAngleInc.setValue(angleIncStart)
            self.ui.doubleSpinBoxEndAngleInc.setValue(angleIncStop)
            self.ui.spinBoxScanStartRow.setValue(startrow)
            self.ui.spinBoxScanStopRow.setValue(stoprow)
            self.ui.spinBoxMachineFrequency.setValue(frequency)
            self.ui.spinBoxAccPulses.setValue(accPulses)
            self.beamoffsetX = self.ui.spinBoxBeamX.value()
            self.beamoffsetY = self.ui.spinBoxBeamY.value()
            self.setBeamsize()
            self.setPixelsPerUm()


            topleftx = float(config.get('Grid', 'topleftx'))
            toplefty = float(config.get('Grid', 'toplefty'))
            toprightx = float(config.get('Grid', 'toprightx'))
            toprighty = float(config.get('Grid', 'toprighty'))
            bottomleftx = float(config.get('Grid', 'bottomleftx'))
            bottomlefty = float(config.get('Grid', 'bottomlefty'))
            bottomrightx = float(config.get('Grid', 'toprightx'))
            bottomrighty = float(config.get('Grid', 'toprighty'))
            centerx  = -float(config.get('Grid', 'centerx'))
            centery  = -float(config.get('Grid', 'centery'))
            angle  = float(config.get('Grid', 'angle'))
            offsetx  = float(config.get('Grid', 'offsetx'))
            offsety  = float(config.get('Grid', 'offsety'))
            width  = float(config.get('Grid', 'width'))
            height  = float(config.get('Grid', 'height'))
            
            
            topLeftPos = QtCore.QPointF(topleftx, toplefty)
            topRightPos = QtCore.QPointF(toprightx, toprighty)
            bottomLeftPos = QtCore.QPointF(bottomleftx, bottomlefty)
            bottomRightPos = QtCore.QPointF(bottomrightx, bottomrighty)
            centerPos = QtCore.QPointF(centerx, centery)
            offsetPos = QtCore.QPointF(offsetx, offsety)
            
            try:
                self.raster.raster.setAllCorners(topLeftPos)
                self.raster.raster.expandRight(width)
                self.raster.raster.expandBottom(height)
                self.raster.raster.rotate(angle=angle,anchor=topLeftPos)
                self.raster.updateRaster()
            except:
                print "Error loading grid."
                print sys.exc_info()
            
            #self.raster.updateRaster()
            #self.raster.raster.setTopLeft(topLeftPos)
            #self.raster.raster.setTopRight(topRightPos)
            #self.raster.raster.setBottomRight(bottomRightPos)
            #self.raster.raster.setBottomLeft(bottomLeftPos)
            #self.raster.raster.center = centerPos
            #self.raster.raster.setAngle(angle)
            #self.raster.raster.setOffset(offsetPos)
            
            #self.raster.raster.move(centerPos,um=False)
            
            
            #self.raster.raster.setC
            #self.center = QtCore.QPointF(raster.center)
            
            #self.raster.raster.rotate(gridAngle)

    def doGrid(self):

        self.definingTopLeft = True
        self.raster.scene().parent().setCursor(Qt.CrossCursor)
        self.ui.pushButtonSetTopLeft.setEnabled(False)
        self.ui.doubleSpinBoxTopLeftX.setValue(self.topLeftPos.x()/self.raster.conversion.getValue())
        self.ui.doubleSpinBoxTopLeftY.setValue(-self.topLeftPos.y()/self.raster.conversion.getValue())
        self.topLeftEllipseItem = QtGui.QGraphicsEllipseItem(self.topLeftPos.x()-5, self.topLeftPos.y()-5, 10, 10)
        self.topLeftEllipseItem.setPen(QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
        self.topLeftEllipseItem.setBrush(Qt.red)
        self.sceneLiveview.addItem(self.topLeftEllipseItem)
        self.ui.checkBoxTopLeftCorner.setCheckState(True)
        self.ui.pushButtonSetTopRight.setEnabled(False)
        self.definingTopLeft = False
         
        self.definingTopRight = False
        self.ui.doubleSpinBoxTopRightX.setValue(self.topRightPos.x()/self.raster.conversion.getValue())
        self.ui.doubleSpinBoxTopRightY.setValue(-self.topRightPos.y()/self.raster.conversion.getValue())
        self.topRightEllipseItem = QtGui.QGraphicsEllipseItem(self.topRightPos.x()-5, self.topRightPos.y()-5, 10, 10)
        self.topRightEllipseItem.setPen(QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
        self.topRightEllipseItem.setBrush(Qt.red)
        self.sceneLiveview.addItem(self.topRightEllipseItem)
        self.ui.checkBoxTopRightCorner.setCheckState(True)
        self.ui.pushButtonSetBottomLeft.setEnabled(False)
        self.definingTopRight = False
        
        self.definingBottomLeft = True
        deltaY = float(self.topLeftPos.y()-self.topRightPos.y())
        deltaX = float(self.topRightPos.x()-self.topLeftPos.x())
        k = -deltaY/deltaX
        m = self.topLeftPos.y()-k*self.topLeftPos.x()
        k_ortho = -1.0/k
        m_ortho = self.topLeftPos.y()- k_ortho*self.topLeftPos.x()
        x_bottom = (self.virtualHeight/2-m_ortho)/k_ortho
        self.orthoLine = QtCore.QLineF(self.topLeftPos.x(),self.topLeftPos.y(),x_bottom,self.virtualHeight/2)
        self.orthoLineItem = QtGui.QGraphicsLineItem(self.orthoLine)
        self.abLine = QtCore.QLineF(self.topRightPos,self.topLeftPos)
        self.abLineItem = QtGui.QGraphicsLineItem(self.abLine)
        #print abLine.angleTo(self.orthoLine)
        linePenOrtho = QtGui.QPen(QtGui.QColor(Qt.green), 4, Qt.DashLine)
        self.orthoLineItem.setPen(linePenOrtho)
        linePenAb = QtGui.QPen(QtGui.QColor(Qt.yellow), 4, Qt.DashLine)
        self.abLineItem.setPen(linePenAb)
        #self.sceneLiveview.addLine(self.orthoLine,linePen)
        self.sceneLiveview.addItem(self.orthoLineItem)
        self.sceneLiveview.addItem(self.abLineItem)
         
        self.definingBottomLeft = False
        self.ui.doubleSpinBoxBottomLeftX.setValue(self.bottomLeftPos.x()/self.raster.conversion.getValue())
        self.ui.doubleSpinBoxBottomLeftY.setValue(-self.bottomLeftPos.y()/self.raster.conversion.getValue())
         
        self.bottomLeftEllipseItem = QtGui.QGraphicsEllipseItem(self.bottomLeftPos.x()-5, self.bottomLeftPos.y()-5, 10, 10)
        self.bottomLeftEllipseItem.setPen(QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
        self.bottomLeftEllipseItem.setBrush(Qt.red)
        self.sceneLiveview.addItem(self.bottomLeftEllipseItem)
        
        self.ui.checkBoxBottomLeftCorner.setCheckState(True)
        
        deltaY = self.topRightPos.y()-self.topLeftPos.y()
        deltaX = self.topRightPos.x()-self.topLeftPos.x()
        
        a = numpy.arctan(deltaY/deltaX)
        
        
        self.raster.raster.setTopRight(self.topRightPos, um=False)
        self.raster.rotate(-numpy.degrees(a))
        
        self.raster.raster.setTopLeft(self.topLeftPos, um=False)
        
        self.raster.raster.setBottomLeft(self.bottomLeftPos, um=False)
        print self.raster.raster.getTopRight(), self.raster.raster.getTopLeft(), self.raster.raster.getBottomLeft()
        
        scanPos1=self.raster.getScanPositions()[0]
        print self.raster.raster.getTopRight(), self.raster.raster.getTopLeft(), self.raster.raster.getBottomLeft()
        self.raster.updateRaster()
        print self.raster.raster.getTopRight(), self.raster.raster.getTopLeft(), self.raster.raster.getBottomLeft()
        #self.raster.raster.expandRight(2*10*self.raster.conversion.getValue())
        #print self.raster.raster.getTopRight(), self.raster.raster.getTopLeft(), self.raster.raster.getBottomLeft()
        #self.raster.raster.expandBottom(2*10*self.raster.conversion.getValue())
        #print self.raster.raster.getTopRight(), self.raster.raster.getTopLeft(), self.raster.raster.getBottomLeft()
        
        tl = self.topLeftPos/self.raster.conversion.getValue()
        print self.raster.raster.getTopRight(), self.raster.raster.getTopLeft(), self.raster.raster.getBottomLeft()
        #self.raster.raster.move(tl-scanPos1)
        print self.raster.raster.getTopRight(), self.raster.raster.getTopLeft(), self.raster.raster.getBottomLeft()
        self.raster.updateRaster()
        
        
    def saveSettings(self):
        config = ConfigParser.ConfigParser()
        config.read(self.settingsFile)
        
        #save settings
        config.set("SavedSettings","scale",self.ui.doubleSpinBoxPixelsPerUm.value())
        config.set("SavedSettings","holepitch",self.ui.doubleSpinBoxHolePitch.value())
        config.set("SavedSettings","gridangle",self.ui.doubleSpinBoxAngle.value())
        config.set("SavedSettings","yzpitch",self.ui.doubleSpinBoxYZpitch.value())
        config.set("SavedSettings","beamsize",self.ui.doubleSpinBoxBeamsize.value())
        config.set("SavedSettings","beamx",self.ui.spinBoxBeamX.value())
        config.set("SavedSettings","beamy",self.ui.spinBoxBeamY.value())
        config.set("SavedSettings","scanname",self.ui.lineEditScanName.text())
        config.set("SavedSettings","angleincstart",self.ui.doubleSpinBoxStartAngleInc.value())
        config.set("SavedSettings","angleincstop",self.ui.doubleSpinBoxEndAngleInc.value())
        config.set("SavedSettings","startrow",self.ui.spinBoxScanStartRow.value())
        config.set("SavedSettings","stoprow",self.ui.spinBoxScanStopRow.value())
        config.set("SavedSettings","frequency",self.ui.spinBoxMachineFrequency.value())
        config.set("SavedSettings","accpulses",self.ui.spinBoxAccPulses.value())
        
        
        
        
        if self.raster is not None:
            grid = self.raster.raster.getScanRows()
            if grid is not None and (len(grid) > 0):

                config.set("Grid","topleftx",self.raster.raster.getTopLeft(um=False).x())
                config.set("Grid","toplefty",self.raster.raster.getTopLeft(um=False).y())
                config.set("Grid","toprightx",self.raster.raster.getTopRight(um=False).x())
                config.set("Grid","toprighty",self.raster.raster.getTopRight(um=False).y())
                config.set("Grid","bottomleftx",self.raster.raster.getBottomLeft(um=False).x())
                config.set("Grid","bottomlefty",self.raster.raster.getBottomLeft(um=False).y())
                config.set("Grid","bottomrightx",self.raster.raster.getBottomRight(um=False).x())
                config.set("Grid","bottomrighty",self.raster.raster.getBottomRight(um=False).y())
                config.set("Grid","centerx",self.raster.raster.center.x())
                config.set("Grid","centery",self.raster.raster.center.y())
                config.set("Grid","angle",self.raster.raster.angle)
                config.set("Grid","offsetx",self.raster.raster.getOffset().x())
                config.set("Grid","offsety",self.raster.raster.getOffset().y())
                config.set("Grid","width",self.raster.raster.getWidth(um=False))
                config.set("Grid","height",self.raster.raster.getHeight(um=False))
        
        with open(self.settingsFile, 'wb') as configfile:
            config.write(configfile)
            
    def eventFilter(self, obj, event):
        
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Return:
                w = self.focusWidget() 
                if (w == self.ui.doubleSpinBoxHolePitch):
                    self.setHolePitch()
                if (w == self.ui.doubleSpinBoxPixelsPerUm):
                    self.setPixelsPerUm()
                if (w == self.ui.spinboxExposureTime):
                    self.setExposureTime(self.ui.spinboxExposureTime.value())
                if (w == self.ui.spinboxGain):
                    self.setGain(self.ui.spinboxGain.value())
                if (w == self.ui.spinBoxBeamX):
                    self.beamoffsetX = self.ui.spinBoxBeamX.value()
                    self.saveSettings()
                if (w == self.ui.spinBoxBeamY):
                    self.beamoffsetY = self.ui.spinBoxBeamY.value()
                    self.saveSettings()
                if (w == self.ui.doubleSpinBoxScanXposition):
                    self.motorThread.setScanX(self.ui.doubleSpinBoxScanXposition.value())
                if (w == self.ui.doubleSpinBoxScanYposition):
                    self.motorThread.setScanY(self.ui.doubleSpinBoxScanYposition.value())
                if (w == self.ui.doubleSpinBoxGonioAngle):
                    self.motorThread.setGonio(self.ui.doubleSpinBoxGonioAngle.value())                    
                if (w == self.ui.doubleSpinBoxGonioAngle_2):
                    self.motorThread.setGonio(self.ui.doubleSpinBoxGonioAngle_2.value())
                if (w == self.ui.doubleSpinBoxGonioZposition):
                    self.motorThread.setGonioZ(self.ui.doubleSpinBoxGonioZposition.value())
                if (w == self.ui.doubleSpinBoxOnaxisXposition):
                    self.motorThread.setOnaxisX(self.ui.doubleSpinBoxOnaxisXposition.value())
                if (w == self.ui.doubleSpinBoxOnaxisYposition):
                    self.motorThread.setOnaxisY(self.ui.doubleSpinBoxOnaxisYposition.value())
                if (w == self.ui.doubleSpinBoxOnaxisZposition):
                    self.motorThread.setOnaxisZ(self.ui.doubleSpinBoxOnaxisZposition.value())
                if (w == self.ui.doubleSpinBoxBeamstopXposition):
                    self.motorThread.setBeamstopX(self.ui.doubleSpinBoxBeamstopXposition.value())
                if (w == self.ui.doubleSpinBoxBeamstopYposition):
                    self.motorThread.setBeamstopY(self.ui.doubleSpinBoxBeamstopYposition.value())
                
                    
                if (w == self.ui.doubleSpinBoxGonioAngle_calib):
                    self.motorThread.calibrateGonio(self.ui.doubleSpinBoxGonioAngle_calib.value())
                if (w == self.ui.doubleSpinBoxGoniometerZposition_calib):
                    self.motorThread.calibrateGonioZ(self.ui.doubleSpinBoxGoniometerZposition_calib.value())
                if (w == self.ui.doubleSpinBoxOnaxisXposition_calib):
                    self.motorThread.calibrateOnaxisX(self.ui.doubleSpinBoxOnaxisXposition_calib.value())
                if (w == self.ui.doubleSpinBoxOnaxisYposition_calib):
                    self.motorThread.calibrateOnaxisY(self.ui.doubleSpinBoxOnaxisYposition_calib.value())
                if (w == self.ui.doubleSpinBoxOnaxisZposition_calib):
                    self.motorThread.calibrateOnaxisZ(self.ui.doubleSpinBoxOnaxisZposition_calib.value())
                if (w == self.ui.doubleSpinBoxBeamstopXposition_calib):
                    self.motorThread.calibrateBeamstopX(self.ui.doubleSpinBoxBeamstopXposition_calib.value())
                if (w == self.ui.doubleSpinBoxBeamstopYposition_calib):
                    self.motorThread.calibrateBeamstopY(self.ui.doubleSpinBoxBeamstopYposition_calib.value())
                if (w == self.ui.spinBoxGotoRowNumber):
                    self.goToRowHole()
                if (w == self.ui.spinBoxGotoHoleNumber):
                    self.goToRowHole()
        w = self.focusWidget()
        if(event.type() == QtCore.QEvent.GraphicsSceneMouseMove and self.settingBeamPosition):
            self.sceneLiveview.parent().setCursor(Qt.CrossCursor)
            
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and obj == self.sceneLiveview:
            if (event.button() == Qt.RightButton) and not (self.sceneLiveview.parent().cursor().shape() == 7 or self.sceneLiveview.parent().cursor().shape() == 8 ):
                
                mousePos = event.scenePos()

                if not self.ui.checkBoxSinCosCorrection.isChecked():
                    self.setScanX((mousePos.x()+self.beamoffsetX)/self.raster.conversion.getValue())
                    self.setScanY((mousePos.y()+self.beamoffsetY)/self.raster.conversion.getValue())
                else:
                    angle = self.motorThread.currentGonio
                    currX = self.motorThread.currentScanX
                    currY = self.motorThread.currentScanY
                    newX = mousePos.x()/self.raster.conversion.getValue()
                    newY = mousePos.y()/self.raster.conversion.getValue()
                    incrementX = newX-currX
                    incrementY = newY-currY
                    deltaX = incrementX*math.sin(math.radians(angle))
                    deltaY = incrementY*math.sin(math.radians(angle))
                    
                    
                    
            if self.settingBeamPosition and (event.button() == Qt.LeftButton):
                mousePos = self.ui.graphicsviewLiveview.mapFromScene(event.scenePos())
                self.beamoffsetX = int((self.ui.graphicsviewLiveview.viewport().size().width()/2)-mousePos.x())  
                self.beamoffsetY = int((self.ui.graphicsviewLiveview.viewport().size().height()/2)-mousePos.y())
                self.ui.spinBoxBeamX.setValue(self.beamoffsetX)
                self.ui.spinBoxBeamY.setValue(self.beamoffsetY)
                self.settingBeamPosition = False
                return QtGui.QMainWindow.eventFilter(self, obj, event)
            if self.definingTopLeft:
                self.topLeftPos = event.scenePos()
                self.ui.doubleSpinBoxTopLeftX.setValue(self.topLeftPos.x()/self.raster.conversion.getValue())
                self.ui.doubleSpinBoxTopLeftY.setValue(-self.topLeftPos.y()/self.raster.conversion.getValue())
                self.topLeftEllipseItem = QtGui.QGraphicsEllipseItem(event.scenePos().x()-5, event.scenePos().y()-5, 10, 10)
                self.topLeftEllipseItem.setPen(QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
                self.topLeftEllipseItem.setBrush(Qt.red)
                self.sceneLiveview.addItem(self.topLeftEllipseItem)
                self.ui.checkBoxTopLeftCorner.setCheckState(True)
                self.ui.pushButtonSetTopRight.setEnabled(True)
                self.definingTopLeft = False
                 
            elif self.definingTopRight:
                self.topRightPos = event.scenePos()
                self.ui.doubleSpinBoxTopRightX.setValue(self.topRightPos.x()/self.raster.conversion.getValue())
                self.ui.doubleSpinBoxTopRightY.setValue(-self.topRightPos.y()/self.raster.conversion.getValue())
                self.topRightEllipseItem = QtGui.QGraphicsEllipseItem(event.scenePos().x()-5, event.scenePos().y()-5, 10, 10)
                self.topRightEllipseItem.setPen(QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
                self.topRightEllipseItem.setBrush(Qt.red)
                self.sceneLiveview.addItem(self.topRightEllipseItem)
                self.ui.checkBoxTopRightCorner.setCheckState(True)
                self.ui.pushButtonSetBottomLeft.setEnabled(True)
                self.definingTopRight = False
                deltaY = float(self.topLeftPos.y()-self.topRightPos.y())
                deltaX = float(self.topRightPos.x()-self.topLeftPos.x())
                k = -deltaY/deltaX
                m = self.topLeftPos.y()-k*self.topLeftPos.x()
                k_ortho = -1.0/k
                m_ortho = self.topLeftPos.y()- k_ortho*self.topLeftPos.x()
                x_bottom = (self.virtualHeight/2-m_ortho)/k_ortho
                self.orthoLine = QtCore.QLineF(self.topLeftPos.x(),self.topLeftPos.y(),x_bottom,self.virtualHeight/2)
                self.orthoLineItem = QtGui.QGraphicsLineItem(self.orthoLine)
                self.abLine = QtCore.QLineF(self.topRightPos,self.topLeftPos)
                self.abLineItem = QtGui.QGraphicsLineItem(self.abLine)
                #print abLine.angleTo(self.orthoLine)
                linePenOrtho = QtGui.QPen(QtGui.QColor(Qt.green), 4, Qt.DashLine)
                self.orthoLineItem.setPen(linePenOrtho)
                linePenAb = QtGui.QPen(QtGui.QColor(Qt.yellow), 4, Qt.DashLine)
                self.abLineItem.setPen(linePenAb)
                #self.sceneLiveview.addLine(self.orthoLine,linePen)
                self.sceneLiveview.addItem(self.orthoLineItem)
                self.sceneLiveview.addItem(self.abLineItem)
                 
            elif self.definingBottomLeft:
                self.definingBottomLeft = False
                self.bottomLeftPos = event.scenePos()
                self.ui.doubleSpinBoxBottomLeftX.setValue(self.bottomLeftPos.x()/self.raster.conversion.getValue())
                self.ui.doubleSpinBoxBottomLeftY.setValue(-self.bottomLeftPos.y()/self.raster.conversion.getValue())
                 
                self.bottomLeftEllipseItem = QtGui.QGraphicsEllipseItem(event.scenePos().x()-5, event.scenePos().y()-5, 10, 10)
                self.bottomLeftEllipseItem.setPen(QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
                self.bottomLeftEllipseItem.setBrush(Qt.red)
                self.sceneLiveview.addItem(self.bottomLeftEllipseItem)
                
                self.ui.checkBoxBottomLeftCorner.setCheckState(True)
                
                deltaY = self.topRightPos.y()-self.topLeftPos.y()
                deltaX = self.topRightPos.x()-self.topLeftPos.x()
                
                a = numpy.arctan(deltaY/deltaX)
                
                
                self.raster.raster.setAllCorners(self.topLeftPos - ((self.raster.beamsize.getValue() * self.raster.conversion.getValue()) / 2))
                bottomRightPos = self.topLeftPos + (self.raster.beamsize.getValue() / self.raster.conversion.getValue()) / 2
                self.raster.raster.setBottomRight(bottomRightPos, um=False)
                self.raster.rotate(-numpy.degrees(a))
                self.raster.raster.expandRight(self.topRightPos - self.topLeftPos)
                self.raster.raster.expandBottom(self.bottomLeftPos - self.topLeftPos)
                scanPos1=self.raster.getScanPositions()[0]
                self.raster.updateRaster()
                
#                self.raster.raster.expandRight(2*self.ui.doubleSpinBoxHolePitch.value()*self.raster.conversion.getValue())
#                self.raster.raster.expandBottom(2*self.ui.doubleSpinBoxHolePitch.value()*self.raster.conversion.getValue())
                
#                tl = self.topLeftPos/self.raster.conversion.getValue()
#                self.raster.raster.move(tl-scanPos1)
#                self.raster.updateRaster()

        return QtGui.QMainWindow.eventFilter(self, obj, event)
    def connectCamera(self):
        print "camera host/port:", self.cameraServer, self.cameraPort
        self.camera = MjpgStream(self.cameraServer, self.cameraPort)
        self.camera.setImageSize(self.ui.graphicsviewLiveview.width(), self.ui.graphicsviewLiveview.height(), Qt.KeepAspectRatio,rotation=None)
        self.connect(self.camera,SIGNAL("newFrame()"),self.frameGrabbed)
        #self.camera.sendCmd("FixedRate", MjpgStream.IN_CMD_AVT_FRAME_START_TRIGGER_MODE) # set to fixed rate
        #self.camera.sendCmd(10000, MjpgStream.IN_CMD_AVT_FRAMERATE) # fixed rate in miliHz
        #self.camera.sendCmd("Continuous", MjpgStream.IN_CMD_AVT_ACQUISITION_MODE) # acquisition mode continuous
        #self.camera.sendCmd(0, MjpgStream.IN_CMD_AVT_ACQUISITION_START) # start acquisition        self.camera.sendCmd("Manual", MjpgStream.IN_CMD_AVT_GAIN_MODE) # gain mode manual
        gainInfo = self.camera.getCmdInfo(MjpgStream.IN_CMD_AVT_GAIN_VALUE)
        if(gainInfo):
            self.ui.spinboxGain.setMinimum(int(gainInfo['min']))
            self.ui.spinboxGain.setMaximum(int(gainInfo['max']))
            self.ui.spinboxGain.setValue(int(gainInfo['value']))
            self.cameraOnline = True 
        else:
            self.cameraOnline = False
            return # likely connection refused
        #self.camera.sendCmd("Manual", MjpgStream.IN_CMD_AVT_EXPOSURE_MODE) # exposure mode manual
        exposureInfo = self.camera.getCmdInfo(MjpgStream.IN_CMD_AVT_EXPOSURE_VALUE)
        if(exposureInfo):
            self.ui.spinboxExposureTime.setMinimum(int(exposureInfo['min']))
            #self.ui.spinBoxCameraExposureTime.setMaximum(int(exposureInfo['max']))
            self.ui.spinboxExposureTime.setMaximum(200000)
            self.ui.spinboxExposureTime.setValue(int(exposureInfo['value']))
        #self.setCameraZoom(0)
        self.camera.sendCmd(95, MjpgStream.IN_CMD_JPEG_QUALITY)
        
        self.camera.start(QtCore.QThread.LowPriority)
        time.sleep(1)
        
    def SaveImage(self):
        timestring = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        pixmap = QtGui.QPixmap.grabWidget(self.ui.graphicsviewLiveview)
        pixmap.save(timestring+".jpg", "JPG", 95)
        
    def setExposureTime(self,value=0):
        self.camera.sendCmd(value, MjpgStream.IN_CMD_AVT_EXPOSURE_VALUE)
    def setGain(self,value=0):
        self.camera.sendCmd(value, MjpgStream.IN_CMD_AVT_GAIN_VALUE)
    def setAutoExposure(self,newState):
        self.ui.checkBoxAutoExposure.blockSignals(True)
        
        if newState: #if auto
            self.ui.checkBoxAutoExposure.setChecked(True)
            self.camera.sendCmd(100000, MjpgStream.IN_CMD_AVT_EXPOSURE_AUTO_MAX)
            self.camera.sendCmd(2, MjpgStream.IN_CMD_AVT_EXPOSURE_MODE)
            self.ui.spinboxExposureTime.setEnabled(False)
        else:
            self.ui.checkBoxAutoExposure.setChecked(False)
            self.ui.spinboxExposureTime.setEnabled(True)
            self.camera.sendCmd(0, MjpgStream.IN_CMD_AVT_EXPOSURE_MODE) 
            exposureInfo = self.camera.getCmdInfo(MjpgStream.IN_CMD_AVT_EXPOSURE_VALUE)
            if(exposureInfo):
                self.ui.spinboxExposureTime.setMinimum(int(exposureInfo['min']))
                self.ui.spinboxExposureTime.setMaximum(200000)
                self.ui.spinboxExposureTime.setValue(int(exposureInfo['value']))
    
        self.ui.checkBoxAutoExposure.blockSignals(False)
    def setAutoGain(self,newState):
        self.ui.checkBoxAutoGain.blockSignals(True)
        
        if newState: #if auto
            self.ui.checkBoxAutoGain.setChecked(True)
            self.camera.sendCmd(2, MjpgStream.IN_CMD_AVT_GAIN_MODE)
            self.ui.spinboxGain.setEnabled(False)
        else:
            self.ui.checkBoxAutoGain.setChecked(False)
            self.ui.spinboxGain.setEnabled(True)
            self.camera.sendCmd(0, MjpgStream.IN_CMD_AVT_GAIN_MODE)
            gainInfo = self.camera.getCmdInfo(MjpgStream.IN_CMD_AVT_GAIN_VALUE)
            if(gainInfo):
                self.ui.spinboxGain.setMinimum(int(gainInfo['min']))
                self.ui.spinboxGain.setMaximum(int(gainInfo['max']))
                self.ui.spinboxGain.setValue(int(gainInfo['value']))
        
        self.ui.checkBoxAutoGain.blockSignals(False)

    def setRasterAngle(self):
        self.raster.angle.setValue(self.ui.doubleSpinBoxAngle.value())
        self.saveSettings()

    def setHolePitch(self):
        value = self.ui.doubleSpinBoxHolePitch.value()
        if self.raster is not None:
            stepsize = self.raster.stepsize.getValue()
            stepsize.setX(value)
            self.raster.stepsize.setValue(stepsize)
            self.raster.updateRaster()
        self.saveSettings()
        
    def setPixelsPerUm(self):
        value = self.ui.doubleSpinBoxPixelsPerUm.value()
        if self.raster is not None:
            self.raster.conversion.setValue(value)
            self.raster.updateRaster()
        self.saveSettings()

    def setBeamPosition(self):
        self.settingBeamPosition = True
        
    def setYZpitch(self):
        if self.raster is not None:
            self.raster.raster.setPitch(self.ui.doubleSpinBoxYZpitch.value())
            self.raster.updateRaster()
        self.saveSettings()
        
    def clearRaster(self):
        self.raster.clear()
        
        self.definingTopLeft = False
        self.definingTopRight = False
        self.definingBottomLeft = False
        self.allCornersDefined = False
        self.topLeftPos = None
        self.topRightPos = None
        self.bottomLeftPos = None
        
        self.ui.checkBoxTopLeftCorner.setChecked(False)
        self.ui.checkBoxTopRightCorner.setChecked(False)
        self.ui.checkBoxBottomLeftCorner.setChecked(False)
        
        try:
            if self.abLineItem is not None:
                self.sceneLiveview.removeItem(self.abLineItem)
            if self.orthoLineItem is not None: 
                self.sceneLiveview.removeItem(self.orthoLineItem)
            if self.topLeftEllipseItem is not None:
                self.sceneLiveview.removeItem(self.topLeftEllipseItem)
            if self.topRightEllipseItem is not None:
                self.sceneLiveview.removeItem(self.topRightEllipseItem)
            if self.bottomLeftEllipseItem is not None:
                self.sceneLiveview.removeItem(self.bottomLeftEllipseItem)
            if self.assistLineItem is not None:
                self.sceneLiveview.removeItem(self.assistLineItem)
                self.assistLineItem = None
        except:
            pass


        self.topLeftEllipseItem = None
        self.topRightEllipseItem = None
        self.bottomLeftEllipseItem = None
        self.bottomRightEllipseItem = None
        
        self.orthoLineItem = None
        self.abLineItem = None
        self.assistLine = None
        self.assistLineItem = None
        self.ui.pushButtonSetTopLeft.setEnabled(True)
        self.ui.pushButtonSetTopRight.setEnabled(False)
        self.ui.pushButtonSetBottomLeft.setEnabled(False)
        
        self.ui.doubleSpinBoxTopLeftX.setValue(0)
        self.ui.doubleSpinBoxTopLeftY.setValue(0)
        self.ui.doubleSpinBoxTopRightX.setValue(0)
        self.ui.doubleSpinBoxTopRightY.setValue(0)
        self.ui.doubleSpinBoxBottomLeftX.setValue(0)
        self.ui.doubleSpinBoxBottomLeftY.setValue(0)
        self.ui.checkBoxOrtholines.setChecked(True)
        self.saveSettings()

        
    def setTopLeft(self):
        self.definingTopLeft = True
        self.raster.scene().parent().setCursor(Qt.CrossCursor)
        self.ui.pushButtonSetTopLeft.setEnabled(False)
        
    def setTopRight(self):
        self.definingTopRight = True
        self.raster.scene().parent().setCursor(Qt.CrossCursor)
        self.ui.pushButtonSetTopRight.setEnabled(False)
        
    def setBottomLeft(self):
        self.definingBottomLeft = True
        self.raster.scene().parent().setCursor(Qt.CrossCursor)
        self.ui.pushButtonSetBottomLeft.setEnabled(False)
        
        
    def setBeamsize(self):
        if self.raster is not None:
            self.raster.raster.setBeamsize(self.ui.doubleSpinBoxBeamsize.value(),self.ui.doubleSpinBoxBeamsize.value())
            self.raster.updateRaster()
        self.saveSettings()
        
    def goToRowHole(self):
        if self.raster is not None:
            row = self.raster.getScanRow(self.ui.spinBoxGotoRowNumber.value()-1)
            if row is not None:
                rowLength = len(row)
                selectedHole = self.ui.spinBoxGotoHoleNumber.value()
                if ((rowLength) < selectedHole):
                    QtGui.QMessageBox.warning(self, 'Error',"This row only contains " + str(rowLength) + " holes", QtGui.QMessageBox.Ok)
                else:
                    self.setScanX(row[selectedHole-1].x())
                    self.setScanY(row[selectedHole-1].y())
            
    def frameGrabbed(self):
        if self.camera.getFrame() is None: return
        if self.ui.checkBoxAutoExposure.isChecked():
            exposureInfo = self.camera.getCmdInfo(MjpgStream.IN_CMD_AVT_EXPOSURE_VALUE)
            if(exposureInfo):
                self.ui.spinboxExposureTime.setValue(int(exposureInfo['value']))
                
        if self.ui.checkBoxAutoGain.isChecked():
            gainInfo = self.camera.getCmdInfo(MjpgStream.IN_CMD_AVT_GAIN_VALUE)
            if(gainInfo):
                self.ui.spinboxGain.setValue(int(gainInfo['value']))
                
        image = self.camera.getFrame().mirrored(True, False)
        
        pixmap = QtGui.QPixmap.fromImage(image)
        item = QtGui.QGraphicsPixmapItem(pixmap)
        item.setZValue(-1)
        item.setPos(self.motorThread.currentScanX*self.raster.conversion.getValue()-self.ui.graphicsviewLiveview.viewport().size().width()/2.0,self.motorThread.currentScanY*self.raster.conversion.getValue()-self.ui.graphicsviewLiveview.viewport().size().height()/2.0)
        
        self.ui.graphicsviewLiveview.centerOn(item)
        self.sceneLiveview.addItem(item)
        try:
            if self.ui.checkBoxAssistline.isChecked():
                if self.topLeftPos is not None:
                    if self.assistLineItem is not None:
                        self.sceneLiveview.removeItem(self.assistLineItem)
                        
                    angle = self.ui.doubleSpinBoxAssistlineAngle.value()
                    length = self.ui.doubleSpinBoxAssistlineLength.value()
                    deltaX = length*math.cos(math.radians(angle))
                    deltaY = length*math.sin(math.radians(angle))
                    
                    endpointX = self.topLeftPos.x()+deltaX
                    endpointY = self.topLeftPos.y()+deltaY
                    
                    self.assistLine = QtCore.QLineF(self.topLeftPos.x(),self.topLeftPos.y(),endpointX,endpointY)
                    self.assistLineItem = QtGui.QGraphicsLineItem(self.assistLine)
                    linePenAssist = QtGui.QPen(QtGui.QColor(Qt.blue), 4, Qt.DashDotLine)
                    self.assistLineItem.setPen(linePenAssist)
                    
                    self.sceneLiveview.addItem(self.assistLineItem)
            else:
                if self.assistLineItem is not None:
                    self.sceneLiveview.removeItem(self.assistLineItem)
                    self.assistLineItem = None
        except:
            pass
         
        if self.ui.checkBoxOrtholines.isChecked():
            self.cornerOrthoLinesRemoved = False
            if self.abLineItem is not None:
                self.sceneLiveview.removeItem(self.abLineItem)
                self.sceneLiveview.addItem(self.abLineItem)
            if self.orthoLineItem is not None: 
                self.sceneLiveview.removeItem(self.orthoLineItem)
                self.sceneLiveview.addItem(self.orthoLineItem)
            if self.topLeftEllipseItem is not None:
                self.sceneLiveview.removeItem(self.topLeftEllipseItem)
                self.sceneLiveview.addItem(self.topLeftEllipseItem)
            if self.topRightEllipseItem is not None:
                self.sceneLiveview.removeItem(self.topRightEllipseItem)
                self.sceneLiveview.addItem(self.topRightEllipseItem)
            if self.bottomLeftEllipseItem is not None:
                self.sceneLiveview.removeItem(self.bottomLeftEllipseItem)
                self.sceneLiveview.addItem(self.bottomLeftEllipseItem)
                
        else:
            if not self.cornerOrthoLinesRemoved:
                if self.abLineItem is not None:
                    self.sceneLiveview.removeItem(self.abLineItem)
                if self.orthoLineItem is not None: 
                    self.sceneLiveview.removeItem(self.orthoLineItem)
                if self.topLeftEllipseItem is not None:
                    self.sceneLiveview.removeItem(self.topLeftEllipseItem)
                if self.topRightEllipseItem is not None:
                    self.sceneLiveview.removeItem(self.topRightEllipseItem)
                if self.bottomLeftEllipseItem is not None:
                    self.sceneLiveview.removeItem(self.bottomLeftEllipseItem)
                self.cornerOrthoLinesRemoved = True
   
        if(self.cameraImageItem is not None):
            self.sceneLiveview.removeItem(self.cameraImageItem)
        self.cameraImageItem = item
        
        
        item.setPos(self.motorThread.currentScanX*self.raster.conversion.getValue()-self.ui.graphicsviewLiveview.viewport().size().width()/2.0,self.motorThread.currentScanY*self.raster.conversion.getValue()-self.ui.graphicsviewLiveview.viewport().size().height()/2.0)
        #self.ui.graphicsviewLiveview.centerOn(item)
        
        
        #ellipseX = (self.motorThread.currentScanX*self.raster.conversion.getValue()-self.ellipseWidth/2)-self.beamoffsetX 
        #ellipseY = (self.motorThread.currentScanY*self.raster.conversion.getValue()-self.ellipseHeight/2)-self.beamoffsetY
        ellipseX = (self.motorThread.currentScanX*self.raster.conversion.getValue())-self.beamoffsetX 
        ellipseY = (self.motorThread.currentScanY*self.raster.conversion.getValue())-self.beamoffsetY
        
        try:
            if self.ellipseItem is not None:
                self.sceneLiveview.removeItem(self.ellipseItem)
        except:
            pass
        self.ui.doubleSpinBoxBeamsize.value()
        #self.ellipseItem = QtGui.QGraphicsEllipseItem(ellipseX-self.ellipseWidth/2,ellipseY-self.ellipseHeight/2,self.ellipseWidth,self.ellipseHeight)
        self.ellipseItem = QtGui.QGraphicsEllipseItem(ellipseX-(self.ui.doubleSpinBoxBeamsize.value()*self.raster.conversion.getValue())/2,ellipseY-(self.ui.doubleSpinBoxBeamsize.value()*self.raster.conversion.getValue())/2,self.ui.doubleSpinBoxBeamsize.value()*self.raster.conversion.getValue(),self.ui.doubleSpinBoxBeamsize.value()*self.raster.conversion.getValue())
        
        
        penEllipse = QtGui.QPen(QtGui.QColor(Qt.red), 2, Qt.SolidLine)
        self.ellipseItem.setPen(penEllipse)
        self.sceneLiveview.addItem(self.ellipseItem)
        self.ui.graphicsviewLiveview.update()

    def updatePositions(self):
        self.ui.labelScanXposition.setText("%.1f " % self.motorThread.currentScanX + unichr(956) + "m")
        self.ui.labelScanYposition.setText("%.1f " % self.motorThread.currentScanY + unichr(956) + "m")
        self.ui.labelGonioAngle.setText("%.3f" % self.motorThread.currentGonio + unichr(176))
        self.ui.labelGonioAngle_2.setText("%.3f" % self.motorThread.currentGonio + unichr(176))
        self.ui.horizontalSliderXPosition.setValue(int(self.motorThread.currentScanX))
        self.ui.verticalSliderYPosition.setValue(int(self.motorThread.currentScanY))
        
        self.ui.labelGonioZposition.setText("%.1f " % self.motorThread.currentGonioZ + unichr(956) + "m")
        self.ui.labelOnaxisXposition.setText("%.1f " % self.motorThread.currentOnaxisX + unichr(956) + "m")
        self.ui.labelOnaxisYposition.setText("%.1f " % self.motorThread.currentOnaxisY + unichr(956) + "m")
        self.ui.labelOnaxisZposition.setText("%.1f " % self.motorThread.currentOnaxisZ + unichr(956) + "m")
        self.ui.labelBeamstopXposition.setText("%.1f " % self.motorThread.currentBeamstopX + unichr(956) + "m")
        self.ui.labelBeamstopYposition.setText("%.1f " % self.motorThread.currentBeamstopY + unichr(956) + "m")
        
        self.ui.checkBoxScanRunning.setChecked(self.motorThread.stateTask1)
        if self.raster is not None:
            grid = self.raster.raster.getScanRows()
            if grid is not None and (len(grid) > 0):
                rowLength = len(grid[0])
                gridHeight = len(grid)
                if (rowLength > 0): 
                    self.ui.spinBoxGridWidth.setValue(rowLength)
                    self.ui.spinBoxGridHeight.setValue(gridHeight)
            else:
                self.ui.spinBoxGridWidth.setValue(0)
        
        if self.motorThread.stateProxyScanX == DevState.MOVING:
            self.ui.labelScanXposition.setStyleSheet("background-color: yellow")
            self.ui.pushButtonLeft.setEnabled(False)
            self.ui.pushButtonRight.setEnabled(False)
        elif self.motorThread.stateProxyScanX == DevState.ON:
            self.ui.labelScanXposition.setStyleSheet("background-color: lightgreen")
            self.ui.pushButtonLeft.setEnabled(True)
            self.ui.pushButtonRight.setEnabled(True)
        else:
            self.ui.labelScanXposition.setStyleSheet("background-color: red")
            self.ui.pushButtonLeft.setEnabled(False)
            self.ui.pushButtonRight.setEnabled(False)
        
        if self.motorThread.stateProxyScanY == DevState.MOVING:
            self.ui.labelScanYposition.setStyleSheet("background-color: yellow")
            self.ui.pushButtonUp.setEnabled(False)
            self.ui.pushButtonDown.setEnabled(False)
        elif self.motorThread.stateProxyScanY == DevState.ON:
            self.ui.labelScanYposition.setStyleSheet("background-color: lightgreen")
            self.ui.pushButtonUp.setEnabled(True)
            self.ui.pushButtonDown.setEnabled(True)
        else:
            self.ui.labelScanYposition.setStyleSheet("background-color: red")
            self.ui.pushButtonUp.setEnabled(False)
            self.ui.pushButtonDown.setEnabled(False)
            
            
        if self.motorThread.inMountPosition:
            self.ui.pushButtonSetMountPosition.setText("Set sample position")
        else:
            self.ui.pushButtonSetMountPosition.setText("Set mount position")

        if self.motorThread.stateProxyOnaxisZ == DevState.MOVING or self.autofocus is not None:
            self.ui.pushButtonSetMountPosition.setEnabled(False)
        else:
            self.ui.pushButtonSetMountPosition.setEnabled(True)
            
        
        if self.motorThread.stateProxyGonio == DevState.MOVING:
            self.ui.labelGonioAngle.setStyleSheet("background-color: yellow")
            self.ui.labelGonioAngle_2.setStyleSheet("background-color: yellow")
        elif self.motorThread.stateProxyGonio == DevState.ON:
            self.ui.labelGonioAngle.setStyleSheet("background-color: lightgreen")
            self.ui.labelGonioAngle_2.setStyleSheet("background-color: lightgreen")
        else:
            self.ui.labelGonioAngle.setStyleSheet("background-color: red")
            self.ui.labelGonioAngle_2.setStyleSheet("background-color: red")
             
        if self.motorThread.stateProxyGonioZ == DevState.MOVING:
            self.ui.labelGonioZposition.setStyleSheet("background-color: yellow")
        elif self.motorThread.stateProxyGonioZ == DevState.ON:
            self.ui.labelGonioZposition.setStyleSheet("background-color: lightgreen")
        else:
            self.ui.labelGonioZposition.setStyleSheet("background-color: red")
            
        if self.motorThread.stateProxyOnaxisX == DevState.MOVING:
            self.ui.labelOnaxisXposition.setStyleSheet("background-color: yellow")
        elif self.motorThread.stateProxyOnaxisX == DevState.ON:
            self.ui.labelOnaxisXposition.setStyleSheet("background-color: lightgreen")   
        else:
            self.ui.labelOnaxisXposition.setStyleSheet("background-color: red")
            
        if self.motorThread.stateProxyOnaxisY == DevState.MOVING:
            self.ui.labelOnaxisYposition.setStyleSheet("background-color: yellow")
        elif self.motorThread.stateProxyOnaxisY == DevState.ON:
            self.ui.labelOnaxisYposition.setStyleSheet("background-color: lightgreen")   
        else:
            self.ui.labelOnaxisYposition.setStyleSheet("background-color: red")  
             
        if self.motorThread.stateProxyOnaxisZ == DevState.MOVING:
            self.ui.labelOnaxisZposition.setStyleSheet("background-color: yellow")
            self.ui.pushButtonSetMountPosition.setEnabled(False)
        elif self.motorThread.stateProxyOnaxisZ == DevState.ON:
            self.ui.labelOnaxisZposition.setStyleSheet("background-color: lightgreen")
            self.ui.pushButtonSetMountPosition.setEnabled(True)   
        else:
            self.ui.labelOnaxisZposition.setStyleSheet("background-color: red")
             
        if self.motorThread.stateProxyBeamstopX == DevState.MOVING:
            self.ui.labelBeamstopXposition.setStyleSheet("background-color: yellow")
        elif self.motorThread.stateProxyBeamstopX == DevState.ON:
            self.ui.labelBeamstopXposition.setStyleSheet("background-color: lightgreen")   
        else:
            self.ui.labelBeamstopXposition.setStyleSheet("background-color: red")
            
        if self.motorThread.stateProxyBeamstopY == DevState.MOVING:
            self.ui.labelBeamstopYposition.setStyleSheet("background-color: yellow")
        elif self.motorThread.stateProxyBeamstopY == DevState.ON:
            self.ui.labelBeamstopYposition.setStyleSheet("background-color: lightgreen")   
        else:
            self.ui.labelBeamstopYposition.setStyleSheet("background-color: red")

    def setStepSize(self):
        self.ui.doubleSpinBoxScanXposition.setSingleStep(float((self.ui.comboBoxStepSize.currentText()[:-3])))
        self.ui.doubleSpinBoxScanYposition.setSingleStep(float((self.ui.comboBoxStepSize.currentText()[:-3])))
    
    def setStepSize2(self):
        self.ui.doubleSpinBoxGonioZposition.setSingleStep(float((self.ui.comboBoxStepSize_2.currentText()[:-3])))
        self.ui.doubleSpinBoxOnaxisXposition.setSingleStep(float((self.ui.comboBoxStepSize_2.currentText()[:-3])))
        self.ui.doubleSpinBoxOnaxisYposition.setSingleStep(float((self.ui.comboBoxStepSize_2.currentText()[:-3])))
        self.ui.doubleSpinBoxOnaxisZposition.setSingleStep(float((self.ui.comboBoxStepSize_2.currentText()[:-3])))
        self.ui.doubleSpinBoxBeamstopXposition.setSingleStep(float((self.ui.comboBoxStepSize_2.currentText()[:-3])))
        self.ui.doubleSpinBoxBeamstopYposition.setSingleStep(float((self.ui.comboBoxStepSize_2.currentText()[:-3])))
        
    def setScanX(self,position = None):
        if position is None:
            self.motorThread.setScanX(self.ui.doubleSpinBoxScanXposition.value())
        else:
            self.motorThread.setScanX(position)
        
    def setScanY(self,position = None):
        if position is None:
            self.motorThread.setScanY(self.ui.doubleSpinBoxScanYposition.value())
        else:
            self.motorThread.setScanY(position)
        
    def stopAll(self):
        self.motorThread.stopMotors()
    
    def moveUp(self):
        current = self.motorThread.currentScanY
        increment = float((self.ui.comboBoxStepSize.currentText()[:-3]))
        newpos = current - increment
        self.motorThread.setScanY(newpos)
        
    def moveDown(self):
        current = self.motorThread.currentScanY
        increment = float((self.ui.comboBoxStepSize.currentText()[:-3]))
        newpos = current + increment
        self.motorThread.setScanY(newpos)
        
    def moveLeft(self):
        current = self.motorThread.currentScanX
        increment = float((self.ui.comboBoxStepSize.currentText()[:-3]))
        newpos = current - increment
        self.motorThread.setScanX(newpos)
        
    def moveRight(self):
        current = self.motorThread.currentScanX
        increment = float((self.ui.comboBoxStepSize.currentText()[:-3]))
        newpos = current + increment
        self.motorThread.setScanX(newpos)
        
    def moveZero(self):
        self.motorThread.setScanX(0)
        self.motorThread.setScanY(0)
        
    def setTopLeftCoarse(self):
        self.topLeftCoarse = (self.motorThread.currentScanX,self.motorThread.currentScanY)
    def moveTopLeft(self):
        self.setScanX(self.topLeftCoarse[0])
        self.setScanY(self.topLeftCoarse[1])
    def moveTopRight(self):
        self.setScanX(self.topLeftCoarse[0]+1200)
        self.setScanY(self.topLeftCoarse[1])
    def moveBottomRight(self):
        self.setScanX(self.topLeftCoarse[0]+1200)
        self.setScanY(self.topLeftCoarse[1]+1200)
    def moveBottomLeft(self):
        self.setScanX(self.topLeftCoarse[0])
        self.setScanY(self.topLeftCoarse[1]+1200)
    def moveCentre(self):
        self.setScanX(self.topLeftCoarse[0]+600)
        self.setScanY(self.topLeftCoarse[1]+600)
    def setMountPosition(self):
        if self.motorThread.inMountPosition:
            self.motorThread.setMountPosition(False)
        else:
            self.motorThread.setMountPosition(True)
            
    def startScan(self):
        self.saveSettings()
        if self.LCLScollector is None:
            self.filesystem.setSample(str(self.ui.lineEditScanName.text()))
            print "filesystem path:", self.filesystem.getPath(self.filesystem.FS_ROOT_LOCAL+self.filesystem.FS_SUB_PROCESSED+self.filesystem.FS_TYPE_SCAN,True)
        
            self.raster.raster.setOffset(self.beamoffsetX/self.raster.conversion.getValue(),self.beamoffsetY/self.raster.conversion.getValue())
            rows = self.raster.raster.getScanRows()
            
            if len(rows) == 0:
                QtGui.QMessageBox.warning(self, 'Error',"No rows found", QtGui.QMessageBox.Ok)
                return
            
            
            self.ui.tabAlignment.setEnabled(False)
            self.ui.groupBoxGrid.setEnabled(False)
            
            self.LCLScollector = LCLScollector(self.motorThread)
            self.LCLScollector.setParameter("scanPoints",rows)
            self.LCLScollector.setParameter("angle",self.ui.doubleSpinBoxAngle.value())
            self.LCLScollector.setParameter("freq",self.ui.spinBoxMachineFrequency.value())
            self.LCLScollector.setParameter("acclPulses",self.ui.spinBoxAccPulses.value())
            self.LCLScollector.setParameter("gonioStart",self.ui.doubleSpinBoxStartAngleInc.value())
            self.LCLScollector.setParameter("gonioStop",self.ui.doubleSpinBoxEndAngleInc.value())
            self.LCLScollector.setParameter("startRow",self.ui.spinBoxScanStartRow.value())
            self.LCLScollector.setParameter("stopRow",self.ui.spinBoxScanStopRow.value())
            
            
            self.LCLScollector.start()
            self.connect(self.LCLScollector,SIGNAL("scanUpdate()"),self.updateScan)
            self.connect(self.LCLScollector,SIGNAL("scanFinished()"),self.scanFinished)
            
            self.ui.pushButtonStartScan.setEnabled(False)
            self.ui.pushButtonAbortScan.setEnabled(True)
            
        else:
            self.LCLScollector.stop()
            self.LCLScollector = None
            self.ui.progressBarScanStatus.setValue(0)
            self.ui.spinBoxCurrentRow.setValue(0)
    def abortScan(self):
        if self.LCLScollector is not None:
            self.ui.progressBarScanStatus.setValue(int(100*self.LCLScollector.percentDone))
            self.ui.spinBoxCurrentRow.setValue(self.LCLScollector.currentRow)
            self.LCLScollector.stop()
        
    def updateScan(self):
        if self.LCLScollector is not None:
            self.ui.progressBarScanStatus.setValue(int(100*self.LCLScollector.percentDone))
            self.ui.spinBoxCurrentRow.setValue(self.LCLScollector.currentRow+1)
        else:
            self.ui.pushButtonStartScan.setEnabled(True)
            self.ui.pushButtonAbortScan.setEnabled(False)
    def scanFinished(self):
        self.ui.progressBarScanStatus.setValue(100)
        if self.LCLScollector is not None: self.LCLScollector.stop()
        self.LCLScollector = None
        self.ui.progressBarScanStatus.setValue(0)
        self.ui.spinBoxCurrentRow.setValue(0)
        self.ui.tabAlignment.setEnabled(True)
        self.ui.groupBoxGrid.setEnabled(True)
        self.ui.pushButtonStartScan.setEnabled(True)
        self.ui.pushButtonAbortScan.setEnabled(False)
    def setMoveOnClick(self,state):
        if(state): #checked
            self.raster.moveToBeam = True
        else:
            self.raster.moveToBeam = False
    def autoFocusGonio(self):
        self.autofocus = AutoFocus(self.camera,DeviceProxy(self.focusDevice2),type=1)
        self.autofocus.start()
        self.connect(self.autofocus,SIGNAL("focusDone()"),self.focusDone)
        self.ui.pushButtonAutofocusGonio.setEnabled(False)
        self.ui.pushButtonAutofocusGonioZ.setEnabled(False)
    def autoFocusGonioZ(self):
        self.autofocus = AutoFocus(self.camera,DeviceProxy(self.focusDevice),type=0)
        self.autofocus.start()
        self.connect(self.autofocus,SIGNAL("focusDone()"),self.focusDone)
        self.ui.pushButtonAutofocusGonio.setEnabled(False)
        self.ui.pushButtonAutofocusGonioZ.setEnabled(False)
    def focusDone(self):
        self.ui.pushButtonAutofocusGonio.setEnabled(True)
        self.ui.pushButtonAutofocusGonioZ.setEnabled(True)
        if self.autofocus.type == 0:
            self.ui.doubleSpinBoxGonioZposition.setValue(self.motorThread.proxyGonioZ.read_attribute("Position").w_value)
        elif self.autofocus.type == 1:
            self.ui.doubleSpinBoxGonioAngle.setValue(self.motorThread.proxyGonio.read_attribute("Position").w_value)
            self.ui.doubleSpinBoxGonioAngle_2.setValue(self.motorThread.proxyGonio.read_attribute("Position").w_value)
        self.autofocus = None
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    app.setStyle(QtGui.QStyleFactory.create("Cleanlooks"))
    app.setPalette(QtGui.QApplication.style().standardPalette())
    myapp = StartQT4()
    myapp.show()
    ret = app.exec_()
    # Your code that must run when the application closes goes here
    sys.exit(ret)

