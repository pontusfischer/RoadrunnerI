# -*- coding: utf-8 -*-

"""Provides a class Raster that fits a raster of scan positions into a rectangle that may be freely resized,
rotated and moved. RasterItem inherits QGraphicsGroupItem and builds a wrapper around Raster, that allows
mouse driven resize, move and rotation.
Depends on PyQt4 and math.

"""

__author__ = "Jan Meyer"
__email__ = "jan.meyer@desy.de"
__copyright__ = "(c)2013 DESY, FS-PE, P11"
__license__ = "GPL"


from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, SIGNAL, QThread
from math import sin, cos, asin, atan2, degrees, radians, sqrt, ceil, floor, isnan


class Raster(QtGui.QPolygonF):
    """QPolygonF inherited class, that fits a raster of scan positions into a rectangle that
    may be freely resized, rotated and moved. The scan positions can be retrieved as a list of
    QPointF objects, where all positions are in um relative to the pixmap center and a given
    offset. If the scan area is smaller than the beamsize, the positions list will be empty. 
    When the raster is rotated, the corner identifiers will also be rotated such, that the angle
    between the connection of the top left and the top right corner and the horizontal of the pixmap
    will be <= 45 degrees and > -45 degrees.
    """

    # point relations to the raster
    RASTER_POS_OUTSIDE = 0
    RASTER_POS_INSIDE = 1
    RASTER_POS_TOP = 2
    RASTER_POS_RIGHT = 3
    RASTER_POS_BOTTOM = 4
    RASTER_POS_LEFT = 5
    RASTER_POS_TOP_LEFT = 6
    RASTER_POS_TOP_RIGHT = 7
    RASTER_POS_BOTTOM_RIGHT = 8
    RASTER_POS_BOTTOM_LEFT = 9

    # flags determining the scan type
    RASTER_SCAN_VERTICAL = 1
    RASTER_SCAN_SNAKE = 2
    RASTER_SCAN_FLIP_HORIZONTAL = 4
    RASTER_SCAN_FLIP_VERTICAL = 8
    RASTER_SCAN_BIDIRECTIONAL = 16
    RASTER_SCAN_TRIANGULAR = 32

    topLeft = None           # coordinates of the upper left corner in pixels, relative to the pixmap center
    topRight = None          # coordinates of the upper right corner in pixels, relative to the pixmap center
    bottomRight = None       # coordinates of the lower right corner in pixels, relative to the pixmap center
    bottomLeft = None        # coordinates of the lower left corner in pixels, relative to the pixmap center
    center = None            # coordinates of the raster center in pixels, relative to the pixmap center
    angle = 0.0              # angle raster in degrees
    unitVectorX = None       # horizontal component of the current unit vector
    unitVectorY = None       # vertical component of the current unit vector
    pitch = 0.0              # pitch angle in degrees
    pitchFactor = 1.0        # the current pitch vector
    stepsizeHorizontal = 0.0 # horizontal stepsize in um
    stepsizeVertical = 0.0   # vertical stepsize in um
    beamsizeHorizontal = 0.0 # horizontal size of the beam markers in um
    beamsizeVertical = 0.0   # vertical size of the beam markers in um
    conversion = 1.0         # conversion factor pixels / um
    offset = None            # offset coordinates for the pixmap center in um as QPointF
    pixmapCenter = None      # coordinates of the pixmap center in pixels as QPointF
    scanType = 0             # flags determining the scan type
    positions = []           # list of scan positions in pixels as QPointFs
    positionsValid = False   # flag if the positon list is valid
    rows = []                # list of scan positions in pixels as QPointFs
    
    scanPointsX = 0          # number of horizontal scan points in the top line
    scanPointsY = 0          # number of lines with scan points

    def __init__(self, raster=None):
        """Initializes the basic settings.
        
        Keyword arguments:
        raster -- If another raster is given here, it's values will be copied
        
        """
        QtGui.QPolygonF.__init__(self)
        if(isinstance(raster, Raster)):
            self.transferValues(raster)
        else:
            self.clear()

    def transferValues(self, raster):
        """Copies the values of a give raster into this instance.
        
        Keyword arguments:
        raster -- The raster which values will be copied
        
        """
        QtGui.QPolygonF.__init__(self)
        if(isinstance(raster, Raster)):
            self.topLeft = QtCore.QPointF(raster.topLeft)
            self.topRight = QtCore.QPointF(raster.topRight)
            self.bottomRight = QtCore.QPointF(raster.bottomRight)
            self.bottomLeft = QtCore.QPointF(raster.bottomLeft)
            self.center = QtCore.QPointF(raster.center)
            self.angle = raster.angle + 0.0
            self.unitVectorX = QtCore.QPointF(raster.unitVectorX)
            self.unitVectorY = QtCore.QPointF(raster.unitVectorY)
            self.stepsizeHorizontal = raster.stepsizeHorizontal + 0.0
            self.stepsizeVertical = raster.stepsizeVertical + 0.0
            self.beamsizeHorizontal = raster.beamsizeHorizontal + 0.0
            self.beamsizeVertical = raster.beamsizeVertical + 0.0
            self.conversion = raster.conversion + 0.0
            if(raster.offset is not None):
                self.offset = QtCore.QPointF(raster.offset.x(),raster.offset.y())
            if(raster.pixmapCenter is not None):
                self.pixmapCenter = QtCore.QPointF(raster.pixmapCenter)
            self.positions = raster.positions
            self.positionsValid = raster.positionsValid
            self.buildPolygon()

    def setTopLeft(self, point, um=True):
        """Sets the coordinates of the upper left corner.
        
        Keyword arguments:
        point -- The new coordinates as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        """
        if(um and self.conversion == 0): return
        if(um):
            point *= self.conversion
        if(self.isEmpty() or point == self.bottomRight):
            self.setAllCorners(point)
            return
        self.setCorner(point, self.RASTER_POS_BOTTOM_RIGHT)

    def getTopLeft(self, um=True):
        """Returns the coordinates of the upper left corner.
        
        Keyword arguments:
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        Return value:
        frame as QImage or None
        
        """
        if(um):
            return self.topLeft / self.conversion
        return self.topLeft

    def setTopRight(self, point, um=True):
        """Sets the coordinates of the upper right corner.
        
        Keyword arguments:
        point -- The new coordinates as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        """
        if(um and self.conversion == 0): return
        if(um):
            point *= self.conversion
        if(self.isEmpty() or point == self.bottomLeft):
            self.setAllCorners(point)
            return
        self.setCorner(point, self.RASTER_POS_BOTTOM_LEFT)

    def getTopRight(self, um=True):
        """Returns the coordinates of the upper right corner.
        
        Keyword arguments:
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        Return value:
        frame as QImage or None
        
        """
        if(um):
            return self.topRight / self.conversion
        return self.topRight

    def setBottomRight(self, point, um=True):
        """Sets the coordinates of the lower right corner.
        
        Keyword arguments:
        point -- The new coordinates as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        """
        if(um and self.conversion == 0): return
        if(um):
            point *= self.conversion
        if(self.isEmpty() or point == self.topLeft):
            self.setAllCorners(point)
            return
        self.setCorner(point, self.RASTER_POS_TOP_LEFT)

    def getBottomRight(self, um=True):
        """Returns the coordinates of the lower right corner.
        
        Keyword arguments:
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        Return value:
        frame as QImage or None
        
        """
        if(um):
            return self.bottomRight / self.conversion
        return self.bottomRight

    def setBottomLeft(self, point, um=True):
        """Sets the coordinates of the lower left corner.
        
        Keyword arguments:
        point -- The new coordinates as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        """
        if(um and self.conversion == 0): return
        if(um):
            point *= self.conversion
        if(self.isEmpty() or point == self.topRight):
            self.setAllCorners(point)
            return
        self.setCorner(point, self.RASTER_POS_TOP_RIGHT)

    def getBottomLeft(self, um=True):
        """Returns the coordinates of the lower left corner.
        
        Keyword arguments:
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        
        Return value:
        frame as QImage or None
        
        """
        if(um):
            return self.bottomLeft / self.conversion
        return self.bottomLeft

    def setCorner(self, point, anchorPos):
        """Sets the coordinates of a corner. anchorPos specifies which corner should be kept static.
        This is taken as the cater-cornered position to the given coordinates. The other two corner are recomputed.
        
        Keyword arguments:
        point -- The new coordinates in pixels as QPointF
        anchorPos -- A constant (like RASTER_POS_TOP_LEFT) specifying the corner that should be kept static.
        
        """
        # determine the anchor point
        if(anchorPos >= self.RASTER_POS_TOP_LEFT and anchorPos <= self.RASTER_POS_BOTTOM_LEFT):
            anchorPos -= 6
        else:
            anchorPos = 0
        points = [self.topLeft, self.topRight, self.bottomRight, self.bottomLeft]
        anchorX = points[anchorPos].x()
        anchorY = points[anchorPos].y()
        pointX = point.x()
        pointY = point.y()
        #tie to chip raster
        if(self.angle == 0.0):
            thirdX = anchorX
            thirdY = point.y()
            width = abs(anchorX - point.x())
            height = abs(point.y() - anchorY)
        else:
            mx = self.unitVectorX.y() / self.unitVectorX.x()
            my = self.unitVectorY.y() / self.unitVectorY.x()
            bx = point.y() - mx * point.x()
            by = anchorY - my * anchorX
            thirdX = (bx - by) / (my - mx)
            thirdY = mx * thirdX + bx
            width = sqrt((thirdX - point.x())**2 + (thirdY - point.y())**2)
            height = sqrt((anchorX - thirdY)**2 + (anchorY - thirdY)**2)
        newWidth = (self.beamsizeHorizontal + round((width / self.conversion - self.beamsizeHorizontal) / self.stepsizeHorizontal) * self.stepsizeHorizontal) * self.conversion
        stepsizeVertical = sqrt(3) * 0.5 * self.stepsizeHorizontal * self.pitchFactor
        newHeight = (self.beamsizeVertical + round((height / self.conversion - self.beamsizeVertical) / stepsizeVertical) * stepsizeVertical) * self.conversion
        diag = sqrt((anchorX - pointX)**2 + (anchorY - pointY)**2)
        angle = -degrees(asin((anchorY - pointY) / diag))
        if(pointX >= anchorX):
            angle = 180 - angle
        elif(pointX < anchorX and pointY < anchorY):
            angle = 360 + angle
        quadrant = int(ceil(angle / 90) - 1) % 4
        if quadrant == 0:
            point2 = QtCore.QPointF(anchorX, anchorY) + self.unitVectorY * newHeight - self.unitVectorX * newWidth
        elif quadrant == 1:
            point2 = QtCore.QPointF(anchorX, anchorY) + self.unitVectorY * newHeight + self.unitVectorX * newWidth
        elif quadrant == 2:
            point2 = QtCore.QPointF(anchorX, anchorY) - self.unitVectorY * newHeight + self.unitVectorX * newWidth
        elif quadrant == 3:
            point2 = QtCore.QPointF(anchorX, anchorY) - self.unitVectorY * newHeight - self.unitVectorX * newWidth
        pointX = point2.x()
        pointY = point2.y()
        #compute relative angle, quadrant and distance of the affected points
        diag = sqrt((anchorX - pointX)**2 + (anchorY - pointY)**2)
        angle = -degrees(asin((anchorY - pointY) / diag))
        if(pointX >= anchorX):
            angle = 180 - angle
        elif(pointX < anchorX and pointY < anchorY):
            angle = 360 + angle
        quadrant = int(ceil(angle / 90) - 1) % 4
        angleTemp = angle
        angle = angle % 90
        if(quadrant == 1 or quadrant == 3):
            angle = -(90 - angle)
        if(quadrant == 1 or quadrant == 2):
            diag = -diag
        length = cos(radians(self.angle - angle)) * diag
        quadrant = int(ceil((angleTemp - self.angle) / 90) - 1) % 4
        #assign new coordinates
        rotPos = [[2, 3, 0, 1], [3, 2, 1, 0], [0, 1, 2, 3], [1, 0, 3, 2]]
        points[rotPos[quadrant][0]].setX(cos(radians(self.angle)) * length + pointX)
        points[rotPos[quadrant][0]].setY(-sin(radians(self.angle )) * length + pointY)
        points[rotPos[quadrant][1]].setX(pointX)
        points[rotPos[quadrant][1]].setY(pointY)
        points[rotPos[quadrant][2]].setX(-cos(radians(self.angle)) * length + anchorX)
        points[rotPos[quadrant][2]].setY(sin(radians(self.angle)) * length + anchorY)
        points[rotPos[quadrant][3]].setX(anchorX)
        points[rotPos[quadrant][3]].setY(anchorY)
        self.center.setX((pointX + anchorX) / 2)
        self.center.setY((pointY + anchorY) / 2)
        self.buildPolygon()

    def setAllCorners(self, point):
        """Initializes the raster to a zero area at the given point.
        
        Keyword arguments:
        point -- The new coordinates in pixels as QPointF
        
        """
        pointX = point.x()
        pointY = point.y()
        self.topLeft.setX(pointX)
        self.topLeft.setY(pointY)
        self.topRight.setX(pointX)
        self.topRight.setY(pointY)
        self.bottomRight.setX(pointX)
        self.bottomRight.setY(pointY)
        self.bottomLeft.setX(pointX)
        self.bottomLeft.setY(pointY)
        self.center.setX(pointX)
        self.center.setY(pointY)
        self.unitVectorX.setX(cos(radians(self.angle)))
        self.unitVectorX.setY(-sin(radians(self.angle)))
        self.unitVectorY.setX(self.unitVectorX.y())
        self.unitVectorY.setY(self.unitVectorX.x())
        self.buildPolygon()

    def expandRight(self, distance):
        """Expands the raster to the right. If distance is given as a QPointF, only it's component in the
        direction of the horizontal unit vector is taken.
        
        Keyword arguments:
        distance -- A numerical value or a QPointF in pixels
        
        """
        if(type(distance) is QtCore.QPointF):
            distance = float(distance.x() * self.unitVectorX.x() + distance.y() * self.unitVectorX.y())
        width = self.getWidth(False)
        newWidth = (self.beamsizeHorizontal + round(((width + distance) / self.conversion - self.beamsizeHorizontal) / self.stepsizeHorizontal) * self.stepsizeHorizontal) * self.conversion
        distance = newWidth - width
        self.topRight += self.unitVectorX * distance
        self.bottomRight += self.unitVectorX * distance
        self.center += self.unitVectorX * (distance / 2)
        if(self.topRight.x() < self.topLeft.x()):
            points = [self.topLeft, self.topRight, self.bottomRight, self.bottomLeft]
            self.topLeft = points[1]
            self.topRight = points[0]
            self.bottomRight = points[3]
            self.bottomLeft = points[2]
        self.buildPolygon()

    def expandBottom(self, distance):
        """Expands the raster to the bottom. If distance is given as a QPointF, only it's component in the
        direction of the vertical unit vector is taken.
        
        Keyword arguments:
        distance -- A numerical value or a QPointF in pixels
        
        """
        if(type(distance) is QtCore.QPointF):
            distance = float(distance.x() * self.unitVectorY.x() + distance.y() * self.unitVectorY.y())
        height = self.getHeight(False)
        stepsizeVertical = sqrt(3) * 0.5 * self.stepsizeHorizontal * self.pitchFactor
        newHeight = (self.beamsizeVertical + round(((height + distance) / self.conversion - self.beamsizeVertical) / stepsizeVertical) * stepsizeVertical) * self.conversion
        distance = newHeight - height
        self.bottomRight += self.unitVectorY * distance
        self.bottomLeft += self.unitVectorY * distance
        self.center += self.unitVectorY * (distance / 2)
        if(self.bottomLeft.y() < self.topLeft.y()):
            points = [self.topLeft, self.topRight, self.bottomRight, self.bottomLeft]
            self.topLeft = points[3]
            self.topRight = points[2]
            self.bottomRight = points[1]
            self.bottomLeft = points[0]
        self.buildPolygon()

    def expandLeft(self, distance):
        """Expands the raster to the left. If distance is given as a QPointF, only it's component in the
        direction of the horizontal unit vector is taken.
        
        Keyword arguments:
        distance -- A numerical value or a QPointF in pixels
        
        """
        if(type(distance) is QtCore.QPointF):
            distance = float(distance.x() * self.unitVectorX.x() + distance.y() * self.unitVectorX.y())
        width = self.getWidth(False)
        newWidth = (self.beamsizeHorizontal + round(((width + distance) / self.conversion - self.beamsizeHorizontal) / self.stepsizeHorizontal) * self.stepsizeHorizontal) * self.conversion
        distance = newWidth - width
        self.topLeft += self.unitVectorX * distance
        self.bottomLeft += self.unitVectorX * distance
        self.center += self.unitVectorX * (distance / 2)
        if(self.topRight.x() < self.topLeft.x()):
            points = [self.topLeft, self.topRight, self.bottomRight, self.bottomLeft]
            self.topLeft = points[1]
            self.topRight = points[0]
            self.bottomRight = points[3]
            self.bottomLeft = points[2]
        self.buildPolygon()

    def expandTop(self, distance):
        """Expands the raster to the top. If distance is given as a QPointF, only it's component in the
        direction of the vertical unit vector is taken.
        
        Keyword arguments:
        distance -- A numerical value or a QPointF in pixels
        
        """
        if(type(distance) is QtCore.QPointF):
            distance = float(distance.x() * self.unitVectorY.x() + distance.y() * self.unitVectorY.y())
        height = self.getHeight(False)
        stepsizeVertical = sqrt(3) * 0.5 * self.stepsizeHorizontal * self.pitchFactor
        newHeight = (self.beamsizeVertical + round(((height + distance) / self.conversion - self.beamsizeVertical) / stepsizeVertical) * stepsizeVertical) * self.conversion
        distance = newHeight - height
        self.topLeft += self.unitVectorY * distance
        self.topRight += self.unitVectorY * distance
        self.center += self.unitVectorY * (distance / 2)
        if(self.bottomLeft.y() < self.topLeft.y()):
            points = [self.topLeft, self.topRight, self.bottomRight, self.bottomLeft]
            self.topLeft = points[3]
            self.topRight = points[2]
            self.bottomRight = points[1]
            self.bottomLeft = points[0]
        self.buildPolygon()

    def move(self, distance, um=True, keepScanPosition=False):
        """Moves the raster on the pixmap. If keepScanPosition is True, the um Coordinates are kept static 
        by modifying the offset.
        
        Keyword arguments:
        distance -- The vector describing the movement as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        keepScanPosition -- Whether the um Positions should be kept static
        
        """
        if(um and self.conversion == 0): return
        if(um):
            distanceUm = distance
            distance *= self.conversion
        else:
            distanceUm = distance / self.conversion
        if(keepScanPosition):
            self.offset += distanceUm
        self.topLeft += distance
        self.topRight += distance
        self.bottomRight += distance
        self.bottomLeft += distance
        self.center += distance
        self.translate(distance)
        self.positionsValid = False

    def rotate(self, angle=0.0, oldPoint=None, newPoint=None, anchor=None):
        """Rotates the raster around an anchor by angle degrees. If oldPoint and newPoint are given,
        their angle difference relative to anchor is taken. If no anchor is given, the center will be used.
        
        Keyword arguments:
        distance -- The vector describing the movement as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        keepScanPosition -- Whether the um Positions should be kept static
        
        """
        if(type(anchor) is QtCore.QPointF):
            rotCenter = anchor
        else:
            rotCenter = self.center
        if(angle == 0.0 and type(oldPoint) is QtCore.QPointF and type(newPoint) is QtCore.QPointF):
            angle = -degrees(atan2((rotCenter.y() - newPoint.y()), (rotCenter.x() - newPoint.x())))
            angle += degrees(atan2((rotCenter.y() - oldPoint.y()), (rotCenter.x() - oldPoint.x())))
        while(angle < 0.0):
            angle += 360.0
        angle = angle % 360.0
        if(self.angle < 0.0):
            oldQuadrant = int(ceil((self.angle + 45.0) / 90.0))
            newQuadrant = int(ceil(((self.angle + angle + 45.0) % 360.0) / 90.0))
        else:
            oldQuadrant = int(ceil((self.angle - 45.0) / 90.0))
            newQuadrant = int(ceil(((self.angle + angle - 45.0) % 360.0) / 90.0))
        self.angle = (self.angle + angle) % 90.0
        if(self.angle > 45.0):
            self.angle = self.angle - 90
        # get anchor relative coordinates
        points = [
            self.topLeft - rotCenter,
            self.topRight - rotCenter,
            self.bottomRight - rotCenter,
            self.bottomLeft - rotCenter,
            self.center - rotCenter,
        ]
        # rotate points
        cosinus = cos(radians(angle))
        sinus = sin(radians(angle))
        for i in range(5):
            if(not points[i].isNull()):
                px = points[i].x()
                py = points[i].y()
                points[i].setX(cosinus * px + sinus * py)
                points[i].setY(-sinus * px + cosinus * py)
        # assign points to their new positions
        rotPos = [[0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1], [3, 0, 1, 2]]
        rotQuad = (newQuadrant - oldQuadrant + 4) % 4
        self.topLeft = points[rotPos[rotQuad][0]] + rotCenter
        self.topRight = points[rotPos[rotQuad][1]] + rotCenter
        self.bottomRight = points[rotPos[rotQuad][2]] + rotCenter
        self.bottomLeft = points[rotPos[rotQuad][3]] + rotCenter
        self.center = points[4] + rotCenter
        # rebuild
        self.unitVectorX = (self.topRight - self.topLeft) / sqrt((self.topRight.x() - self.topLeft.x())**2 + (self.topRight.y() - self.topLeft.y())**2)
        self.unitVectorY.setX(-self.unitVectorX.y())
        self.unitVectorY.setY(self.unitVectorX.x())
        self.buildPolygon()

    def scale(self, factor):
        """Scales the raster by a given factor. The pixmap center is kept constant. The conversion factor is not 
        touched and has to be adjusted manually.
        
        Keyword arguments:
        factor -- A numerical value
        
        """
        if(self.pixmapCenter is None or self.isEmpty()): return
        self.positionsValid = False
        self.topLeft = ((self.topLeft - self.pixmapCenter) * factor) + self.pixmapCenter
        self.topRight = ((self.topRight - self.pixmapCenter) * factor) + self.pixmapCenter
        self.bottomRight = ((self.bottomRight - self.pixmapCenter) * factor) + self.pixmapCenter
        self.bottomLeft = ((self.bottomLeft - self.pixmapCenter) * factor) + self.pixmapCenter
        self.center = ((self.center - self.pixmapCenter) * factor) + self.pixmapCenter
        self.buildPolygon()

    def buildPolygon(self):
        """Builds the graphical outline of the raster.
        
        """
        QtGui.QPolygonF.clear(self)
        self.append(self.topLeft)
        self.append(self.topRight)
        self.append(self.bottomRight)
        self.append(self.bottomLeft)
        self.append(self.topLeft)
        self.positionsValid = False

    def clear(self):
        """Resets the raster to a zero area at 0, 0.
        
        """
        self.topLeft = QtCore.QPointF(0, 0)
        self.topRight = QtCore.QPointF(0, 0)
        self.bottomRight = QtCore.QPointF(0, 0)
        self.bottomLeft = QtCore.QPointF(0, 0)
        self.center = QtCore.QPointF(0, 0)
        self.angle = 0.0
        self.unitVectorX = QtCore.QPointF(1, 0)
        self.unitVectorY = QtCore.QPointF(0, -1)
        QtGui.QPolygonF.clear(self)
        self.positionsValid = False

    def pointRelation(self, point, distance):
        """Returns whether a certain point is next to a line or corner or inside or outside the raster.
        
        Keyword arguments:
        point -- The coordinates in pixels as QPointF
        distance -- the tolerance as a numerical value in pixels
        
        Return value:
        A RASTER_POS constant
        
        """
        if(self.isEmpty()):
            return self.RASTER_POS_OUTSIDE
        elif(sqrt((self.topLeft.x() - point.x())**2 + (self.topLeft.y() - point.y())**2) <= distance):
            return self.RASTER_POS_TOP_LEFT
        elif(sqrt((self.topRight.x() - point.x())**2 + (self.topRight.y() - point.y())**2) <= distance):
            return self.RASTER_POS_TOP_RIGHT
        elif(sqrt((self.bottomRight.x() - point.x())**2 + (self.bottomRight.y() - point.y())**2) <= distance):
            return self.RASTER_POS_BOTTOM_RIGHT
        elif(sqrt((self.bottomLeft.x() - point.x())**2 + (self.bottomLeft.y() - point.y())**2) <= distance):
            return self.RASTER_POS_BOTTOM_LEFT
        elif(self.topLeft == self.topRight or self.topLeft == self.bottomLeft or self.bottomLeft == self.bottomRight or self.topRight == self.bottomRight):
            return self.RASTER_POS_OUTSIDE
        else:
            distanceTop = sqrt(((self.topRight.y()-self.topLeft.y())*(point.x()-self.topLeft.x())-(self.topRight.x()-self.topLeft.x())*(point.y()-self.topLeft.y()))**2 \
                    / ((self.topRight.x()-self.topLeft.x())**2 + (self.topRight.y()-self.topLeft.y())**2))
            distanceRight = sqrt(((self.bottomRight.y()-self.topRight.y())*(point.x()-self.topRight.x())-(self.bottomRight.x()-self.topRight.x())*(point.y()-self.topRight.y()))**2 \
                    / ((self.bottomRight.x()-self.topRight.x())**2 + (self.bottomRight.y()-self.topRight.y())**2))
            distanceBottom = sqrt(((self.bottomLeft.y()-self.bottomRight.y())*(point.x()-self.bottomRight.x())-(self.bottomLeft.x()-self.bottomRight.x())*(point.y()-self.bottomRight.y()))**2 \
                    / ((self.bottomLeft.x()-self.bottomRight.x())**2 + (self.bottomLeft.y()-self.bottomRight.y())**2))
            distanceLeft = sqrt(((self.topLeft.y()-self.bottomLeft.y())*(point.x()-self.bottomLeft.x())-(self.topLeft.x()-self.bottomLeft.x())*(point.y()-self.bottomLeft.y()))**2 \
                    / ((self.topLeft.x()-self.bottomLeft.x())**2 + (self.topLeft.y()-self.bottomLeft.y())**2))
            if(distanceTop <= distance and distanceRight + distanceLeft - 0.1 <= \
                    sqrt((self.topRight.x() - self.topLeft.x())**2 + (self.topRight.y() - self.topLeft.y())**2)):
                return self.RASTER_POS_TOP
            elif(distanceRight <= distance and distanceTop + distanceBottom - 0.1 <= \
                    sqrt((self.bottomLeft.x() - self.topLeft.x())**2 + (self.bottomLeft.y() - self.topLeft.y())**2)):
                return self.RASTER_POS_RIGHT
            elif(distanceBottom <= distance and distanceRight + distanceLeft - 0.1 <= \
                    sqrt((self.topRight.x() - self.topLeft.x())**2 + (self.topRight.y() - self.topLeft.y())**2)):
                return self.RASTER_POS_BOTTOM
            elif(distanceLeft <= distance and distanceTop + distanceBottom - 0.1 <= \
                    sqrt((self.bottomLeft.x() - self.topLeft.x())**2 + (self.bottomLeft.y() - self.topLeft.y())**2)):
                return self.RASTER_POS_LEFT
            elif(distanceRight + distanceLeft - 0.1 <= \
                    sqrt((self.topRight.x() - self.topLeft.x())**2 + (self.topRight.y() - self.topLeft.y())**2) and \
                    distanceTop + distanceBottom - 0.1 <= \
                    sqrt((self.bottomLeft.x() - self.topLeft.x())**2 + (self.bottomLeft.y() - self.topLeft.y())**2)):
                return self.RASTER_POS_INSIDE
            else:
                return self.RASTER_POS_OUTSIDE

    def setPixmapSize(self, x=0.0, y=None):
        """Sets the size of the pixmap. This is important because all coordinates are relative to the center
        of this pixmap.
        
        Keyword arguments:
        x -- The width as numerical value in pixels or a QPointF containing the size.
        y -- The height as numerical value in pixels
        
        """
        if(type(x) is QtCore.QPointF):
            self.pixmapCenter = QtCore.QPointF(x.x() / 2, x.y() / 2)
        else:
            self.pixmapCenter = QtCore.QPointF(x / 2, y / 2)
        self.positionsValid = False

    def setAngle(self, angle):
        """Sets absolute angle of the raster. It describes the angle between the pixmap horizontal and the
        line connecting the top left and the top right corners of the raster.
        The corner identifiers are rotated such, that angle is always <= 45 degrees and > -45 degrees.
        
        Keyword arguments:
        angle -- A numerical value in degrees
        
        """
        self.rotate(angle - self.angle)

    def getAngle(self):
        """Returns the absolute angle of the raster.
        
        Return value:
        The angle in degrees
        
        """
        return self.angle

    def setPitch(self, angle):
        """Sets absolute angle of the raster. It corrects for the misalignment around the horizontal axis.
        
        Keyword arguments:
        angle -- A numerical value in degrees
        
        """
        self.pitch = angle
        self.pitchFactor = cos(radians(angle))
        self.positionsValid = False

    def getPitch(self):
        """Returns the pitch angle in degrees.
        
        Return value:
        The angle in degrees
        
        """
        return self.pitch

    def setOffset(self, x=0.0, y=None):
        """Sets the offset of the pixmap center in um.
        
        Keyword arguments:
        x -- The horizontal offset as numerical value or a QPointF containing the coordinates.
        y -- The vertical offset as numerical value
        
        """
        if(type(x) is QtCore.QPointF):
            self.offset = QtCore.QPointF(x.x(), x.y())
        else:
            self.offset = QtCore.QPointF(x, y)

    def getOffset(self):
        """Returns the offset of the pixmap center in um.
        
        Return value:
        A QPointF
        
        """
        return self.offset

    def setConversion(self, x=0.0):
        """Sets the conversion factor.
        
        Keyword arguments:
        x -- The conversion factor in pixels / um as numerical value.
       
        """
        self.conversion = x
        self.positionsValid = False

    def getConversion(self):
        """Returns the conversion factor.
        
        Return value:
        A numerical value in pixels / um
        
        """
        return self.conversion

    def setBeamsize(self, x=0.0, y=None):
        """Sets the beamsize in um.
        
        Keyword arguments:
        x -- The beam width as numerical value or a QPointF containing the size.
        y -- The beam height as numerical value
        
        """
        if(type(x) is QtCore.QPointF):
            self.beamsizeHorizontal = x.x()
            self.beamsizeVertical = x.y()
        else:
            self.beamsizeHorizontal = x
            self.beamsizeVertical = y
        self.positionsValid = False

    def getBeamsize(self):
        """Returns the beamsize in um.
        
        Return value:
        A QPointF
        
        """
        return QtCore.QPointF(self.beamsizeHorizontal, self.beamsizeVertical)

    def setStepsize(self, x=0.0, y=None):
        """Sets the stepsize in um. In triangular mode, the y value will be ignored.
        
        Keyword arguments:
        x -- The stepsize as numerical value or a QPointF containing the size.
        y -- The stepsize as numerical value
        
        """
        if(type(x) is QtCore.QPointF):
            self.stepsizeHorizontal = x.x()
            self.stepsizeVertical = x.y()
        else:
            self.stepsizeHorizontal = x
            self.stepsizeVertical = y
        self.positionsValid = False

    def getStepsize(self):
        """Returns the stepsize in um.
        
        Return value:
        A QPointF
        
        """
        return QtCore.QPointF(self.stepsizeHorizontal, self.stepsizeVertical)

    def setScanType(self, type):
        """Sets the scan type, specified by a combination of scan type constant flags.
        
        Keyword arguments:
        type -- A combination of scan type constant flags.
        
        """
        type = int(type)
        if(type >= 0 and type < 64):
            self.scanType = type
            self.positionsValid = False

    def getScanType(self):
        """Returns the scan type.
        
        Return value:
        A combination of scan type constant flags.
        
        """
        return self.scanType

    def setWidth(self, width, um=True):
        """Sets the width of the raster. It is shrunk or expanded around the center.
        
        Keyword arguments:
        width -- The new width as numerical value
        um -- Whether the width is in pixels (False) or in um (True), Defaults to True
        
        """
        if(um and self.conversion == 0): return
        if(um):
            width = width * self.conversion
        increase = width - self.getWidth(um=False) / 2
        self.expandLeft(increase)
        self.expandRight(increase)

    def getWidth(self, um=True):
        """Returns the width of the raster.
        
        Keyword arguments:
        um -- Whether the width is in pixels (False) or in um (True), Defaults to True
        
        Return value:
        A numerical value
        
        """
        if(um and self.conversion == 0): return 0.0
        if(um):
            return sqrt((self.topRight.x() - self.topLeft.x())**2 + (self.topRight.y() - self.topLeft.y())**2) / self.conversion
        else:
            return sqrt((self.topRight.x() - self.topLeft.x())**2 + (self.topRight.y() - self.topLeft.y())**2)

    def setHeight(self, height, um=True):
        """Sets the height of the raster. It is shrunk or expanded around the center.
        
        Keyword arguments:
        width -- The new height as numerical value
        um -- Whether the height is in pixels (False) or in um (True), Defaults to True
        
        """
        if(um and self.conversion == 0): return
        if(um):
            height = height * self.conversion
        increase = height - self.getHeight(um=False) / 2
        self.expandTop(increase)
        self.expandBottom(increase)

    def getHeight(self, um=True):
        """Returns the height of the raster.
        
        Keyword arguments:
        um -- Whether the height is in pixels (False) or in um (True), Defaults to True
        
        Return value:
        A numerical value
        
        """
        if(um and self.conversion == 0): return 0.0
        if(um):
            return sqrt((self.bottomLeft.x() - self.topLeft.x())**2 + (self.bottomLeft.y() - self.topLeft.y())**2) / self.conversion
        else:
            return sqrt((self.bottomLeft.x() - self.topLeft.x())**2 + (self.bottomLeft.y() - self.topLeft.y())**2)

    def getScanRow(self, i):
        """Returns a list of scan positions in um considering the dimensions, angle, stepsize and scan type.
        
        Return value:
        A list of QPointF
        
        """
        if(not self.positionsValid):
            self.calculateScanPositions()
        if(self.positions == [] or self.offset is None or self.pixmapCenter is None): return None
        positions = []
        for pos in self.rows[i]:
            #positions.append((pos - self.pixmapCenter) / self.conversion + self.offset)
            positions.append((pos) / self.conversion + self.offset)
        return positions

    def getScanRows(self):
        """Returns a list of rows of scan positions in um considering the dimensions, angle, stepsize and scan type.
        
        Return value:
        A list of QPointF
        
        """
        if(not self.positionsValid):
            self.calculateScanPositions()
        rows = []
        for row in self.rows:
            positions = []
            for pos in row:
                #positions.append((pos - self.pixmapCenter) / self.conversion + self.offset)
                positions.append((pos) / self.conversion + self.offset)
            rows.append(positions)
        return rows

    def getScanPositions(self):
        """Returns a list of scan positions in um considering the dimensions, angle, stepsize and scan type.
        
        Return value:
        A list of QPointF
        
        """
        if(not self.positionsValid):
            self.calculateScanPositions()
        if(self.positions == [] or self.offset is None or self.pixmapCenter is None): return None
        positions = []
        for pos in self.positions:
            #positions.append((pos - self.pixmapCenter) / self.conversion + self.offset)
            positions.append((pos) / self.conversion + self.offset)
        if(self.scanType & Raster.RASTER_SCAN_BIDIRECTIONAL):
            positionsBack = list(positions)
            positionsBack.pop()
            positionsBack.reverse()
            positions.extend(positionsBack)
        return positions

    def getScanPositionSymbols(self):
        """Returns a QGraphicsItemGroup containing ellipses and numbers for all scan points.
        
        Return value:
        A QGraphicsItemGroup
        
        """
        if(not self.positionsValid):
            self.calculateScanPositions()
        if(self.positions == [] or self.beamsizeHorizontal == 0 or self.beamsizeVertical == 0): return None
        beamsizeHorizontal = self.conversion * self.beamsizeHorizontal
        beamsizeVertical = self.conversion * self.beamsizeVertical
        symbols = QtGui.QGraphicsItemGroup()
        i = 0
        for pos in self.positions:
            ellipse = QtGui.QGraphicsEllipseItem(pos.x()-beamsizeHorizontal/2, pos.y()-beamsizeVertical/2, beamsizeHorizontal, beamsizeVertical)
            ellipse.setPen(QtGui.QPen(QtGui.QColor(Qt.green), 1, Qt.SolidLine))
            ellipse.setBrush(Qt.green)
            ellipse.setOpacity(0.2)
            
            #text = QtGui.QGraphicsSimpleTextItem(str(i+1))
            #text.setFont((QtGui.QFont ("Courier", 5)))
            #textBounds = text.boundingRect()
            #text.setPos(pos.x() - textBounds.width() / 2, pos.y() - textBounds.height() / 2)
            symbols.addToGroup(ellipse)
            #symbols.addToGroup(text)
            i += 1
        return symbols

    def calculateScanPositions(self):
        """Calculates a list of scan positions in pixels considering the dimensions, angle, stepsize and scan type.
        
        """
        if(self.stepsizeHorizontal == 0 or self.stepsizeVertical == 0 or self.conversion == 0):
            self.positions = []
            return
        stepsizeHorizontal = self.conversion * self.stepsizeHorizontal
        stepsizeVertical = self.conversion * self.pitchFactor * self.stepsizeVertical
        if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR):
            if(self.scanType & Raster.RASTER_SCAN_VERTICAL):
                stepsizeHorizontal = self.conversion * sqrt(3) * 0.5 * self.stepsizeHorizontal
                #stepsizeHorizontal = self.conversion * self.stepsizeHorizontal
                stepsizeVertical = self.conversion * self.stepsizeHorizontal * self.pitchFactor
            else:
                stepsizeVertical = self.conversion * sqrt(3) * 0.5 * self.stepsizeHorizontal * self.pitchFactor
                #stepsizeVertical = self.conversion * self.stepsizeHorizontal
        width = sqrt((self.topRight.x() - self.topLeft.x())**2 + (self.topRight.y() - self.topLeft.y())**2)
        height = sqrt((self.bottomLeft.x() - self.topLeft.x())**2 + (self.bottomLeft.y() - self.topLeft.y())**2)
        #print "width",width,"stepsizeHorizontal",stepsizeHorizontal
        if isnan(width): width = 0.0
        if isnan(height): height = 0.0
        
        #stepsHorizontal = int(floor((width - self.beamsizeHorizontal * self.conversion) / stepsizeHorizontal)) + 1
        #stepsVertical = int(floor((height - self.beamsizeVertical * self.conversion) / stepsizeVertical)) + 1
        #stepOffsetHorizontal = (width - stepsHorizontal * stepsizeHorizontal) / 2
        #stepOffsetVertical = (height - stepsVertical * stepsizeVertical) / 2
        stepsHorizontal = int(round((width - self.beamsizeHorizontal * self.conversion) / stepsizeHorizontal)) + 1
        stepsVertical = int(round((height - self.beamsizeVertical * self.conversion) / stepsizeVertical)) + 1
        stepOffsetHorizontal = self.beamsizeHorizontal * self.conversion / 2
        stepOffsetVertical = self.beamsizeVertical * self.conversion / 2
        self.positions = []
        self.rows = []
        posistionsHorizontal = []
        posistionsVertical = []
        for x in range(stepsHorizontal):
            posistionsHorizontal.append(self.unitVectorX * (x * stepsizeHorizontal + stepOffsetHorizontal))
            #posistionsHorizontal.append(self.unitVectorX * ((x + 0.5) * stepsizeHorizontal + stepOffsetHorizontal))
        for y in range(stepsVertical):
            posistionsVertical.append(self.unitVectorY * (y * stepsizeVertical + stepOffsetVertical))
        if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR):
            positionsTriangular = []
            stepOffsetTriangular = self.conversion * 0.5 * self.stepsizeHorizontal
            if(self.scanType & Raster.RASTER_SCAN_VERTICAL):
                for y in range(stepsVertical - 1):
                    positionsTriangular.append(self.unitVectorY * (y * stepsizeVertical + stepOffsetVertical + stepOffsetTriangular))
            else:
                for x in range(stepsHorizontal - 1):
                    #positionsTriangular.append(self.unitVectorX * ((x + 0.5) * stepsizeHorizontal + stepOffsetHorizontal + stepOffsetTriangular))
                    positionsTriangular.append(self.unitVectorX * (x * stepsizeHorizontal + stepOffsetHorizontal + stepOffsetTriangular))
        if(self.scanType & Raster.RASTER_SCAN_FLIP_HORIZONTAL):
            posistionsHorizontal.reverse()
            if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR and not self.scanType & Raster.RASTER_SCAN_VERTICAL):
                positionsTriangular.reverse()
        if(self.scanType & Raster.RASTER_SCAN_FLIP_VERTICAL):
            posistionsVertical.reverse()
            if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR and self.scanType & Raster.RASTER_SCAN_VERTICAL):
                positionsTriangular.reverse()
        if(self.scanType & Raster.RASTER_SCAN_VERTICAL):
            for horz in posistionsHorizontal:
                for vert in posistionsVertical:
                    self.positions.append(self.topLeft + horz + vert)
                if(self.scanType & Raster.RASTER_SCAN_SNAKE):
                    posistionsVertical.reverse()
                    if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR):
                        positionsTriangular.reverse() 
                if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR):
                    temp = posistionsVertical
                    posistionsVertical = positionsTriangular
                    positionsTriangular = temp
        else:
            i = 0
            for vert in posistionsVertical:
                self.rows.append([])
                for horz in posistionsHorizontal:
                    self.positions.append(self.topLeft + horz + vert)
                    self.rows[i].append(self.topLeft + horz + vert)
                if(self.scanType & Raster.RASTER_SCAN_SNAKE):
                    posistionsHorizontal.reverse()
                    if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR):
                        positionsTriangular.reverse() 
                if(self.scanType & Raster.RASTER_SCAN_TRIANGULAR):
                    temp = posistionsHorizontal
                    posistionsHorizontal = positionsTriangular
                    positionsTriangular = temp
                i += 1
        self.positionsValid = True


class RasterEventFilter(QtCore.QObject):
    """Helper class to grab Qt signals from a QGraphicsScene and forward them to an eventFilter in 
    the parent object. This is necessary because QGraphicItems may not inherit QObject.
    
    """

    parent = None # The object that contains the eventFilter to call
    scene = None  # The QGraphicsScene to grab signals from

    def __init__(self, parent):
        """Initializes to object and sets the parent.
        
        Keyword arguments:
        parent -- The object containing the eventFilter.
        
        """
        QtCore.QObject.__init__(self)
        self.parent = parent

    def install(self, scene):
        """Installs the event filter to the scene.
        
        Keyword arguments:
        scene -- The QGraphicsScene to grab signals from.
        
        """
        self.remove()
        self.scene = scene
        self.scene.installEventFilter(self)

    def remove(self):
        """Removes the event filter off the QGraphicsScene.
        
        """
        if(self.scene is not None):
            self.scene.removeEventFilter(self)

    def eventFilter(self, obj, event):
        """The eventFilter, that will only forward the event to the eventFilter in the parent object.
        
        Keyword arguments:
        obj -- The object that raised the signal.
        event -- The signal fired.
        
        """
        return self.parent.eventFilter(obj, event)


class RasterIntValue(QtCore.QObject):
    """Helper class to signal value changes of type int.
    
    """

    getterFunction = None  # function to get the value
    setterFunction = None  # function to set the value
    triggerFunction = None # optional function to call when value is set

    def __init__(self, getterFunction, setterFunction, triggerFunction=None):
        """Initializes to object and sets the hook functions.
        
        Keyword arguments:
        getterFunction -- The function to get the value
        setterFunction -- The function to set the value
        triggerFunction -- The optional function to call when value is set
        
        """
        QtCore.QObject.__init__(self)
        self.getterFunction = getterFunction
        self.setterFunction = setterFunction
        self.triggerFunction = triggerFunction

    def getValue(self):
        """Returns the value.
        
        Return value:
        An int value
        
        """
        return self.getterFunction()

    def setValue(self, value):
        """Sets the value, fires valueChanged signals and optionally calls the trigger function.
        
        Keyword arguments:
        value -- An int value
        
        """
        try:
            value = int(value)
        except:
            return
        self.setterFunction(value)
        if(self.triggerFunction is not None):
            self.triggerFunction()
        self.emit(SIGNAL("valueChanged(int)"), self.getterFunction())
        self.emit(SIGNAL("valueChanged()"))

    def emitValueChanged(self):
        """Fires valueChanged and valueEdited signals.
        
        """
        self.emit(SIGNAL("valueChanged(int)"), self.getterFunction())
        self.emit(SIGNAL("valueChanged()"))
        self.emit(SIGNAL("valueEdited(int)"), self.getterFunction())
        self.emit(SIGNAL("valueEdited()"))


class RasterFloatValue(QtCore.QObject):
    """Helper class to signal value changes of type float.
    
    """

    getterFunction = None  # function to get the value
    setterFunction = None  # function to set the value
    triggerFunction = None # optional function to call when value is set

    def __init__(self, getterFunction, setterFunction, triggerFunction=None):
        """Initializes to object and sets the hook functions.
        
        Keyword arguments:
        getterFunction -- The function to get the value
        setterFunction -- The function to set the value
        triggerFunction -- The optional function to call when value is set
        
        """
        QtCore.QObject.__init__(self)
        self.getterFunction = getterFunction
        self.setterFunction = setterFunction
        self.triggerFunction = triggerFunction

    def getValue(self):
        """Returns the value.
        
        Return value:
        A float value
        
        """
        return self.getterFunction()

    def setValue(self, value):
        """Sets the value, fires valueChanged signals and optionally calls the trigger function.
        
        Keyword arguments:
        value -- A float value
        
        """
        try:
            value = float(value)
        except:
            return
        self.setterFunction(value)
        if(self.triggerFunction is not None):
            self.triggerFunction()
        self.emit(SIGNAL("valueChanged(double)"), self.getterFunction())
        self.emit(SIGNAL("valueChanged()"))

    def emitValueChanged(self):
        """Fires valueChanged and valueEdited signals.
        
        """
        self.emit(SIGNAL("valueChanged(double)"), self.getterFunction())
        self.emit(SIGNAL("valueChanged()"))
        self.emit(SIGNAL("valueEdited(double)"), self.getterFunction())
        self.emit(SIGNAL("valueEdited()"))


class RasterPointValue(QtCore.QObject):
    """Helper class to signal value changes of type QPointF.
    
    """

    getterFunction = None  # function to get the value
    setterFunction = None  # function to set the value
    triggerFunction = None # optional function to call when value is set

    def __init__(self, getterFunction, setterFunction, triggerFunction=None):
        """Initializes to object and sets the hook functions.
        
        Keyword arguments:
        getterFunction -- The function to get the value
        setterFunction -- The function to set the value
        triggerFunction -- The optional function to call when value is set
        
        """
        QtCore.QObject.__init__(self)
        self.getterFunction = getterFunction
        self.setterFunction = setterFunction
        self.triggerFunction = triggerFunction

    def getValue(self):
        """Returns the value.
        
        Return value:
        A QPointF object
        
        """
        return self.getterFunction()

    def setValue(self, value):
        """Sets the value, fires valueChanged signals and optionally calls the trigger function.
        
        Keyword arguments:
        value -- A QPointF object
        
        """
        if(type(value) != QtCore.QPointF):
            return
        self.setterFunction(value)
        if(self.triggerFunction is not None):
            self.triggerFunction()
        self.emit(SIGNAL("valueChanged(PyQt_PyObject)"), self.getterFunction())
        self.emit(SIGNAL("valueChanged()"))

    def emitValueChanged(self):
        """Fires valueChanged and valueEdited signals.
        
        """
        self.emit(SIGNAL("valueChanged(PyQt_PyObject)"), self.getterFunction())
        self.emit(SIGNAL("valueChanged()"))
        self.emit(SIGNAL("valueEdited(PyQt_PyObject)"), self.getterFunction())
        self.emit(SIGNAL("valueEdited()"))


class RasterItem(QtGui.QGraphicsItemGroup):

    raster = None               # raster object
    rasterItem = None           # QGraphicsPolygonItem build from raster, removed while dragging / rotating
    rasterGroup = None          # the QGraphisItemGroup from Raster.getScanPositionSymbols()
    draggingRaster = None       # a raster object that only exists while dragging or rotating
    draggingRasterItem = None   # QGraphicsPolygonItem build from draggingRaster
    cursorPosition = None       # 
    draggingOrigin = None       # the mouse coordinates where dragging or rotation started
    rasterEventFilter = None    # RasterEventFilter helper object

    moveToBeam = False          # not used by now
    dragging = False            # currently dragging
    rotating = False            # currently rotating

    # raster values made accessible via helper object 
    topLeft = None
    topRight = None
    bottomRight = None
    bottomLeft = None
    angle = None
    pitch = None
    offset = None
    conversion = None
    beamsize = None
    stepsize = None
    width = None
    height = None
    scanType = None

    def __init__(self, parent=None):
        """Initializes the object and sets up a bunch of helper objects.
        
        Keyword arguments:
        parent -- optional QGraphicsItem
        
        """
        QtGui.QGraphicsItemGroup.__init__(self, parent)
        self.raster = Raster()
        self.topLeft = RasterPointValue(self.raster.getTopLeft, self.raster.setTopLeft, self.updateRaster)
        self.topRight = RasterPointValue(self.raster.getTopRight, self.raster.setTopRight, self.updateRaster)
        self.bottomRight = RasterPointValue(self.raster.getBottomRight, self.raster.setBottomRight, self.updateRaster)
        self.bottomLeft = RasterPointValue(self.raster.getBottomLeft, self.raster.setBottomLeft, self.updateRaster)
        self.angle = RasterFloatValue(self.raster.getAngle, self.raster.setAngle, self.updateRaster)
        self.pitch = RasterFloatValue(self.raster.getPitch, self.raster.setPitch, self.updateRaster)
        self.offset = RasterPointValue(self.raster.getOffset, self.raster.setOffset, self.updateRaster)
        self.conversion = RasterFloatValue(self.raster.getConversion, self.raster.setConversion, self.updateRaster)
        self.beamsize = RasterPointValue(self.raster.getBeamsize, self.raster.setBeamsize, self.updateRaster)
        self.stepsize = RasterPointValue(self.raster.getStepsize, self.raster.setStepsize, self.updateRaster)
        self.width = RasterFloatValue(self.raster.getWidth, self.raster.setWidth, self.updateRaster)
        self.height = RasterFloatValue(self.raster.getHeight, self.raster.setHeight, self.updateRaster)
        self.scanType = RasterIntValue(self.raster.getScanType, self.raster.setScanType, self.updateRaster)
        self.rasterEventFilter = RasterEventFilter(self)

    def addPolygon(self, polygonF, pen=None, brush=None):
        """Buils a QGraphicsPolygonItem from polygonF and adds it to the item group.
        
        Keyword arguments:
        polygonF -- A QPolygonF or usually Raster object, which should be visualized 
        pen - QPen that is used to paint the QGraphicsPolygonItem
        brush - QBrush that is used to paint the QGraphicsPolygonItem
        
        """
        if(not isinstance(polygonF, QtGui.QPolygonF)):
            return None
        item = QtGui.QGraphicsPolygonItem(polygonF, self)
        if(pen is not None and type(pen) == QtGui.QPen):
            item.setPen(pen)
        if(brush is not None and type(pen) == QtGui.QBrush):
            item.setBrush(brush)
        self.addToGroup(item)
        return item

    def itemChange(self, change, value):
        """Hook that is called amongst others, when the scene for this item changes. 
        This is used to de-/register the eventFilter.
        
        Keyword arguments:
        change -- Constant describing the event type
        value -- optional Parameter

        """
        if(change == QtGui.QGraphicsItem.ItemSceneChange):
            scene = value.toPyObject()
            if(type(scene) == QtGui.QGraphicsScene):
                self.rasterEventFilter.install(scene)
                self.raster.setPixmapSize(scene.width(), scene.height())
            else:
                self.rasterEventFilter.remove()
        return value

    def eventFilter(self, obj, event):
        """The eventFilter called by an event filter in a helper object that is registered to
        the QGraphicsScene. It handles mouse driven dragging and rotating of the raster.
        
        Keyword arguments:
        obj -- The object that raised the signal.
        event -- The signal fired.
        
        """
        # reset mouse cursor
        if(event.type() == QtCore.QEvent.Leave):
            self.scene().parent().setCursor(Qt.ArrowCursor)
            return False
        elif((event.type() == QtCore.QEvent.GraphicsSceneMouseMove) and not self.moveToBeam):
            # set mouse cursor
            if(not (self.dragging or self.rotating)):
                self.draggingRaster = None
                self.cursorPosition = self.raster.pointRelation(event.scenePos(), 7)
                if(self.cursorPosition == Raster.RASTER_POS_OUTSIDE):
                    self.scene().parent().setCursor(Qt.ArrowCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_INSIDE):
                    self.scene().parent().setCursor(Qt.OpenHandCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_TOP_LEFT):
                    self.scene().parent().setCursor(Qt.SizeFDiagCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_TOP_RIGHT):
                    self.scene().parent().setCursor(Qt.SizeBDiagCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_RIGHT):
                    self.scene().parent().setCursor(Qt.SizeFDiagCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_LEFT):
                    self.scene().parent().setCursor(Qt.SizeBDiagCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_TOP):
                    self.scene().parent().setCursor(Qt.SizeVerCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_RIGHT):
                    self.scene().parent().setCursor(Qt.SizeHorCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM):
                    self.scene().parent().setCursor(Qt.SizeVerCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_LEFT):
                    self.scene().parent().setCursor(Qt.SizeHorCursor)
            else:
                self.draggingRaster = Raster(self.raster)
                # handle dragging
                if(self.dragging):
                    if(self.cursorPosition == Raster.RASTER_POS_INSIDE):
                        self.draggingRaster.move(event.scenePos() - self.draggingOrigin, um=False)
                    elif(self.cursorPosition == Raster.RASTER_POS_TOP_LEFT):
                        self.draggingRaster.setTopLeft(event.scenePos(), um=False)
                    elif(self.cursorPosition == Raster.RASTER_POS_TOP_RIGHT):
                        self.draggingRaster.setTopRight(event.scenePos(), um=False)
                    elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_RIGHT):
                        self.draggingRaster.setBottomRight(event.scenePos(), um=False)
                    elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_LEFT):
                        self.draggingRaster.setBottomLeft(event.scenePos(), um=False)
                    elif(self.cursorPosition == Raster.RASTER_POS_TOP):
                        self.draggingRaster.expandTop(event.scenePos() - self.draggingOrigin)
                    elif(self.cursorPosition == Raster.RASTER_POS_RIGHT):
                        self.draggingRaster.expandRight(event.scenePos() - self.draggingOrigin)
                    elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM):
                        self.draggingRaster.expandBottom(event.scenePos() - self.draggingOrigin)
                    elif(self.cursorPosition == Raster.RASTER_POS_LEFT):
                        self.draggingRaster.expandLeft(event.scenePos() - self.draggingOrigin)
                # handle rotation
                elif(self.rotating):
                    if(self.cursorPosition == Raster.RASTER_POS_TOP_LEFT):
                        self.draggingRaster.rotate(newPoint=event.scenePos(), oldPoint=self.draggingOrigin, anchor=self.draggingRaster.bottomRight)
                    elif(self.cursorPosition == Raster.RASTER_POS_TOP_RIGHT):
                        self.draggingRaster.rotate(newPoint=event.scenePos(), oldPoint=self.draggingOrigin, anchor=self.draggingRaster.bottomLeft)
                    elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_RIGHT):
                        self.draggingRaster.rotate(newPoint=event.scenePos(), oldPoint=self.draggingOrigin, anchor=self.draggingRaster.topLeft)
                    elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_LEFT):
                        self.draggingRaster.rotate(newPoint=event.scenePos(), oldPoint=self.draggingOrigin, anchor=self.draggingRaster.topRight)
                # update edited shape
                if(self.draggingRasterItem is not None):
                    self.removeFromGroup(self.draggingRasterItem)
                    self.draggingRasterItem = None
                if(self.draggingRaster is not None):
                    self.draggingRasterItem = self.addPolygon(self.draggingRaster, QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
                return True
        elif((event.type() == QtCore.QEvent.GraphicsSceneMousePress) and (self.cursorPosition != Raster.RASTER_POS_OUTSIDE or self.raster.isEmpty())):
            # start dragging
            if(event.button() == Qt.LeftButton and not self.rotating and not self.moveToBeam):
                if(self.raster.isEmpty()):
                    self.raster.setAllCorners(event.scenePos())
                    self.draggingRaster = Raster(self.raster)
                    self.draggingRasterItem = self.addPolygon(self.draggingRaster, QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
                    self.cursorPosition = Raster.RASTER_POS_TOP_LEFT
                    self.scene().parent().setCursor(Qt.SizeFDiagCursor)
                    self.draggingOrigin = event.scenePos()
                    self.dragging = True
                    return True
                elif(not self.dragging and self.cursorPosition > Raster.RASTER_POS_OUTSIDE):
                    self.draggingRaster = Raster(self.raster)
                    self.draggingRasterItem = self.addPolygon(self.draggingRaster, QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
                if(self.rasterGroup is not None):
                    self.removeFromGroup(self.rasterGroup)
                if(self.rasterItem is not None):
                    self.removeFromGroup(self.rasterItem)
                self.draggingOrigin = event.scenePos()
                self.dragging = True
                return True
            # start rotation
            elif(event.button() == Qt.RightButton and not self.raster.isEmpty() and not self.dragging):
                if(self.cursorPosition == Raster.RASTER_POS_TOP_LEFT):
                    self.scene().parent().setCursor(Qt.SizeBDiagCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_TOP_RIGHT):
                    self.scene().parent().setCursor(Qt.SizeFDiagCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_RIGHT):
                    self.scene().parent().setCursor(Qt.SizeBDiagCursor)
                elif(self.cursorPosition == Raster.RASTER_POS_BOTTOM_LEFT):
                    self.scene().parent().setCursor(Qt.SizeFDiagCursor)
                self.draggingRaster = Raster(self.raster)
                self.draggingRasterItem = self.addPolygon(self.draggingRaster, QtGui.QPen(QtGui.QColor(Qt.red), 1, Qt.SolidLine))
                if(self.rasterGroup is not None):
                    self.removeFromGroup(self.rasterGroup)
                if(self.rasterItem is not None):
                    self.removeFromGroup(self.rasterItem)
                self.draggingOrigin = event.scenePos()
                self.rotating = True
                return True
        # end dragging or rotation
        elif(event.type() == QtCore.QEvent.GraphicsSceneMouseRelease and (self.dragging or self.rotating)):
            oldRaster = Raster(self.raster)
            self.raster.transferValues(self.draggingRaster)
            #self.raster.setOffset(0.0, 0.0)
            if(self.draggingRasterItem is not None):
                self.removeFromGroup(self.draggingRasterItem)
                self.draggingRasterItem = None
            self.dragging = False
            self.rotating = False
            self.updateRaster()
            self.emitValuesChanged(oldRaster)
            return True
        # forward all unhandled events to the mainwindow handler
        return self.scene().parent().eventFilter(obj, event)

    def updateRaster(self):
        """Rebuilds the raster outline and scan position visualization and triggers a repaint.
        
        """
        if(self.rasterItem is not None):
            self.removeFromGroup(self.rasterItem)
        self.rasterItem = self.addPolygon(self.raster, QtGui.QPen(QtGui.QColor(Qt.green), 1, Qt.SolidLine))
        if(self.rasterGroup is not None):
            self.removeFromGroup(self.rasterGroup)
            self.rasterGroup = None
        self.rasterGroup = self.raster.getScanPositionSymbols()
        if(self.rasterGroup is not None):
            self.addToGroup(self.rasterGroup)
        if(self.scene() is not None):
            self.scene().views()[0].update()

    def emitValuesChanged(self, old):
        """Compares the members of a given old Raster object with the current ones and signals if they
        changed via helper objects.
        
        Keyword arguments:
        old -- The old Raster
        
        """
        if(old.topLeft != self.raster.topLeft):
            self.topLeft.emitValueChanged()
        if(old.topRight != self.raster.topRight):
            self.topRight.emitValueChanged()
        if(old.bottomRight != self.raster.bottomRight):
            self.bottomRight.emitValueChanged()
        if(old.bottomLeft != self.raster.bottomLeft):
            self.bottomLeft.emitValueChanged()
        if(old.angle != self.raster.angle):
            self.angle.emitValueChanged()
        if(old.pitch != self.raster.pitch):
            self.pitch.emitValueChanged()
        if(old.offset != self.raster.offset):
            self.offset.emitValueChanged()
        if(old.conversion != self.raster.conversion):
            self.conversion.emitValueChanged()
        if(old.beamsizeHorizontal != self.raster.beamsizeHorizontal or old.beamsizeVertical != self.raster.beamsizeVertical):
            self.beamsize.emitValueChanged()
        if(old.stepsizeHorizontal != self.raster.stepsizeHorizontal or old.stepsizeVertical != self.raster.stepsizeVertical):
            self.stepsize.emitValueChanged()
        if(old.getWidth() != self.raster.getWidth()):
            self.width.emitValueChanged()
        if(old.getHeight() != self.raster.getHeight()):
            self.height.emitValueChanged()
        if(old.scanType != self.raster.scanType):
            self.scanType.emitValueChanged()

    def move(self, distance, um=True, keepScanPosition=False):
        """Moves the raster on the pixmap. If keepScanPosition is True, the um Coordinates are kept static 
        by modifying the offset. Changes are signaled by helper objects.
        
        Keyword arguments:
        distance -- The vector describing the movement as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        keepScanPosition -- Whether the um Positions should be kept static
        
        """
        oldRaster = Raster(self.raster)
        self.raster.move(distance, um, keepScanPosition)
        self.updateRaster()
        self.emitValuesChanged(oldRaster)

    def rotate(self, angle=0.0, oldPoint=None, newPoint=None, anchor=None):
        """Rotates the raster around an anchor by angle degrees. If oldPoint and newPoint are given,
        their angle difference relative to anchor is taken. If no anchor is given, the center will be used.
        Changes are signaled by helper objects.
        
        Keyword arguments:
        distance -- The vector describing the movement as QPointF
        um -- Whether the coordinates are in pixels (False) or in um (True), Defaults to True
        keepScanPosition -- Whether the um Positions should be kept static
        
        """
        oldRaster = Raster(self.raster)
        self.raster.rotate(angle, oldPoint, newPoint, anchor)
        self.updateRaster()
        self.emitValuesChanged(oldRaster)

    def scale(self, factor):
        """Scales the raster by a given factor. The pixmap center is kept constant. The conversion factor is not 
        touched and has to be adjusted manually. Changes are signaled by helper objects.
        
        Keyword arguments:
        factor -- A numerical value
        
        """
        oldRaster = Raster(self.raster)
        self.raster.scale(factor)
        self.updateRaster()
        self.emitValuesChanged(oldRaster)

    def clear(self):
        """Resets the raster to a zero area at 0, 0. Changes are signaled by helper objects.
        
        """
        oldRaster = Raster(self.raster)
        self.raster.clear()
        self.updateRaster()
        self.emitValuesChanged(oldRaster)

    def getScanPositions(self):
        """Returns a list of scan positions in um considering the dimensions, angle, stepsize and scan type.
        
        Return value:
        A list of QPointF
        
        """
        return self.raster.getScanPositions()

    def getScanRow(self, i):
        """Returns a list of scan positions in um considering the dimensions, angle, stepsize and scan type.
        
        Return value:
        A list of QPointF
        
        """
        return self.raster.getScanRow(i)
