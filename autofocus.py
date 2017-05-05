'''
Created on Jul 9, 2015

@author: pontusfr
'''
from PyQt4.QtCore import SIGNAL, QThread
import time
import numpy
from PyTango import *
from PIL import Image, ImageFilter, ImageChops, ImageStat, ImageDraw
from PyQt4.QtGui import QImage

class AutoFocus(QThread):
    # A thread is started by calling QThread.start() never by calling run() directly!
    def __init__(self,camera,focusdevice,type=0):
        QThread.__init__(self)
        print "Autofocus thread: Starting thread"
        self.camera = camera
        self.focusdevice = focusdevice
        self.type=type
    def stop(self):
        print "Autofocus thread: Stopping thread"
        self.alive = False
        self.wait() # waits until run stops on his own

    def run(self):
        print "Autofocus thread: started"
        self.alive = True
        if self.type == 0: #gonio Z
            #startPos = self.focusdevice.read_attribute("SoftCcwLimit").value
            #stopPos =  self.focusdevice.read_attribute("SoftCwLimit").value
            startPos = -1000
            stopPos =  1200
            stepsize = 40 #micrometers
        elif self.type == 1: #gonio
            startPos = -5
            stopPos =  5
            stepsize = 0.1 #degrees
            
        positions = numpy.arange(startPos,stopPos,stepsize)
        
        contrastArray = numpy.zeros(len(positions))
        for i in range(len(positions)):
            self.focusdevice.write_attribute("Position",positions[i])
            time.sleep(0.05)
            while self.focusdevice.state() == DevState.MOVING:
                time.sleep(0.01)
            #time.sleep(0.1)
            qimage = self.camera.getFrame()
            bytes=qimage.bits().asstring(qimage.numBytes())
            pilimage = Image.frombuffer("L",(qimage.width()+1,qimage.height()),bytes,'raw', "L", 0, 1)
            s=5    
            w,h = pilimage.size
            box = (w/2 - 50, h/2 - 50, w/2 + 50, h/2 + 50)
            pilimage = pilimage.crop(box)
            imf = pilimage.filter(ImageFilter.MedianFilter(s))
            #d = ImageChops.subtract(pilimage, imf, 1, 100)
            d = ImageChops.subtract(pilimage, imf)
            contrastArray[i]=ImageStat.Stat(d).stddev[0]
        
        maxContrast = numpy.argmax(contrastArray)
        
        print "Coarse scan found focus at", positions[maxContrast], ". Refining."
        self.focusdevice.write_attribute("Position",positions[maxContrast])
        time.sleep(0.05)
        while self.focusdevice.state() == DevState.MOVING:
            time.sleep(0.01)
        if self.type == 0: #gonio Z
            startPos = positions[maxContrast]-100
            stopPos =  positions[maxContrast]+100
            stepsize = 4 #micrometers
        elif self.type == 1: #gonio
            startPos = positions[maxContrast]-0.3
            stopPos =  positions[maxContrast]+0.3
            stepsize = 0.05 #degrees

        
        positions = numpy.arange(startPos,stopPos,stepsize)
        
        contrastArray = numpy.zeros(len(positions))
        for i in range(len(positions)):
            self.focusdevice.write_attribute("Position",positions[i])
            time.sleep(0.05)
            while self.focusdevice.state() == DevState.MOVING:
                time.sleep(0.01)
            time.sleep(0.1)
            qimage = self.camera.getFrame()
            bytes=qimage.bits().asstring(qimage.numBytes())
            pilimage = Image.frombuffer("L",(qimage.width()+1,qimage.height()),bytes,'raw', "L", 0, 1)
            s=5           
            w,h = pilimage.size
            box = (w/2 - 50, h/2 - 50, w/2 + 50, h/2 + 50)
            pilimage = pilimage.crop(box)
            imf = pilimage.filter(ImageFilter.MedianFilter(s))
            #d = ImageChops.subtract(pilimage, imf, 1, 100)
            d = ImageChops.subtract(pilimage, imf)
            contrastArray[i]=ImageStat.Stat(d).stddev[0]
        
        maxContrast = numpy.argmax(contrastArray)
        print "Fine scan found focus at", positions[maxContrast]
        self.focusdevice.write_attribute("Position",positions[maxContrast])
        print "Moving to focus point"
        
        
        # exit position of run function of thread. if exiting == true we end up here
        self.valid = 0
        self.status = "OFFLINE"
        
        print "Autofocus thread: died"
        self.emit(SIGNAL("focusDone()"))
        
    def join(self, timeout=None):
        print "Autofocus thread: join method"
        self.alive = False