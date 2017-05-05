import random
import threading,Queue
import time
from PyTango import *
class SimulationAttribute():
        def __init__(self, value):
            self.value = value
            self.w_value = value
            
class SimulationDevice():
        currState = DevState.ON
        currStatus = "Ready"
        
        startPos = 0
        targetPos = 10
        speed = 1000
        moveThread = None
        moveQ = None
        acqThread = None
        acqQ = None
        recvQ = Queue.Queue()
        def __init__(self):
            self.attributes = dict()
            #self.write_attribute("Position", 0)
            #self.write_attribute("VelocityUnits", 1)
            #self.attributes["VelocityUnits"] = 1000
            
        def write_attribute(self, name, value):
            if(name == "Position" or name == "position"):
                startPos = self.read_attribute("Position").value
                targetPos = value
                
                if targetPos > startPos:
                    speed = abs(self.read_attribute("VelocityUnits").value)
                else:
                    speed = -abs(self.read_attribute("VelocityUnits").value)
            
                if (abs(targetPos-startPos) < 0.1): #bullshit
                    return
                
                timeLeftToTravel = abs(targetPos-startPos)/abs(speed)
                
                self.write_attribute("RemainingMoveTime", timeLeftToTravel)
                currPos = startPos
                integrationTime = 0.1
            
                self.currStatus = "MOVING"
                #self.currState = "MOVING"
                self.currState = DevState.MOVING
                
                self.moveQ = Queue.Queue()
                
                
                threadargs = (startPos,targetPos,speed,integrationTime,timeLeftToTravel,self.moveQ,self.recvQ)
                
                stop_moving_state = threading.Thread(target=self.stop_moving_state,args=threadargs)
                stop_moving_state.start()
                
                if self.attributes.has_key(str("AuxiliaryControlAtVelocity")):
                    if self.attributes["AuxiliaryControlAtVelocity"] == 1:
                        self.attributes["ParkingActive"] = 1
                
                return
                
            if self.attributes.has_key(str(name)):
                self.attributes[str(name)] = value
            else:
                self.attributes[str(name)] = value

        def read_attribute(self, name):
            if self.moveQ is not None:
                queueEmpty = False
                while not queueEmpty:
                    try:
                        result = self.moveQ.get(timeout=0.001)
        
                    except Queue.Empty:
                        queueEmpty = True
                        break
                    
                    if result[0] == "currPos":
                        pos = result[1]
                        self.attributes["Position"] = pos
                        
                    if result[0] == "timeLeft":
                        timeLeft = result[1]
                        self.attributes["RemainingMoveTime"] = timeLeft
                        
                    elif result == "done":
                        if self.attributes.has_key(str("AuxiliaryControlAtVelocity")):
                            if self.attributes["AuxiliaryControlAtVelocity"] == 1:
                                self.attributes["ParkingActive"] = 0
                        #self.currState = "ON"
                        self.currState = DevState.ON
                        self.currStatus = "Ready"
                        self.moveThread = None
                        self.moveQ = None
                        queueEmpty = True
                        break
            if self.attributes.has_key(str(name)):
                value = self.attributes[str(name)]
            else:
                if name == "Position":
                    self.attributes[str(name)] = 0
                    value = self.attributes[str(name)]
                else:
                    self.attributes[str(name)] = random.random()
                    value = self.attributes[str(name)]
            return SimulationAttribute(value)

        def command_inout(self,name,value=0):
            if name == "StartStandardAcq":
                self.StartStandardAcq()
            elif name == "StopAcq":
                self.StopAcq()
                
            elif name == "AbortMove":
                self.moveThread = None 
                #self.currState = "ON"
                self.currState = DevState.ON
                self.currStatus = "Ready"
                if self.moveQ is not None:
                    self.recvQ.put("StopMove")
                if self.attributes.has_key(str("AuxiliaryControlAtVelocity")):
                    if self.attributes["AuxiliaryControlAtVelocity"] == 1:
                        self.attributes["ParkingActive"] = 0
            elif (name == "StopMove") :
                self.moveThread = None
                #self.currState = "ON"
                self.currState = DevState.ON
                self.currStatus = "Ready"
                if self.moveQ is not None:
                    self.recvQ.put("StopMove")
                if self.attributes.has_key(str("AuxiliaryControlAtVelocity")):
                    if self.attributes["AuxiliaryControlAtVelocity"] == 1:
                        self.attributes["ParkingActive"] = 0
            elif (name == "Stop") :
                self.moveThread = None
                #self.currState = "ON"
                self.currState = DevState.ON
                self.currStatus = "Ready"
                if self.moveQ is not None:
                    self.recvQ.put("StopMove")
            elif name == "LoadPositionUnits":
                self.attributes["Position"] = value
            elif name == "Calibrate":
                self.attributes["Position"] = value
                
            elif name == "StartUserTask1":
                self.attributes["UserTask1Running"] = True
                threadargs=(2,1)
                stopTask1 = threading.Thread(target=self.stopTask1,args=threadargs)
                stopTask1.start()
                
            return

        def state(self):
            if self.acqQ is not None:
                queueEmpty = False
                while not queueEmpty:
                    try:
                        result = self.acqQ.get(timeout=0.001)
                    except Queue.Empty:
                        queueEmpty = True
                        break
                    if result == "done":
                        self.currState = "ON"
                        self.currStatus = "Acquisition finished"
                        self.acqQ = None
                        self.acqThread = None
                        queueEmpty = True
                        break
                    elif result[0] == "currFrame":
                        frame = result[1]
                        self.currStatus = "Current frame: %d"%frame
                    
            return self.currState
        
        def status(self):
            return self.currStatus
        
        
        
        def stop_moving_state(self,startPos,targetPos,speed,integrationTime,timeLeftToTravel,q,recvQ):
            
            currPos = startPos
            result = ""
            while timeLeftToTravel > 0:
                try:
                    result = recvQ.get(timeout=0.001)
                except Queue.Empty:
                    pass
                else:
                    if result == "StopMove":
                        q.put("done")
                        return
                timeLeftToTravel = timeLeftToTravel-integrationTime
                deltaPos = speed*integrationTime
                currPos = currPos + deltaPos
                
                if timeLeftToTravel < 0: #avoid overshoot due to integration time
                    currPos = targetPos
                if q.qsize() < 2:
                    q.put(("currPos",currPos))
                    q.put(("timeLeft",timeLeftToTravel))
                time.sleep(integrationTime*0.9)
                
            q.put(("currPos",targetPos))
            q.put("done")
            
        def stopTask1(self,travelTime,foo):
            timeLeftToTravel = travelTime
            integrationTime = 0.1
            while timeLeftToTravel > 0:
                time.sleep(integrationTime)
                timeLeftToTravel = timeLeftToTravel-integrationTime
            self.attributes["UserTask1Running"] = False
                        
        def StartStandardAcq(self):
            self.currState = "RUNNING"
            self.currStatus = "Acquiring in simulation mode"
            if not self.attributes.has_key(str("ExposurePeriod")):
                raise Exception("ExposurePeriod not set!")
            if not self.attributes.has_key(str("NbFrames")):
                raise Exception("NbFrames not set!")
                
            self.acqQ = Queue.Queue()
            
            threadargs = (self.attributes["ExposurePeriod"],self.attributes["NbFrames"],self.acqQ,self.recvQ)
            acqThread = threading.Thread(target=self.acqThreadLoop,args=threadargs)
            acqThread.start()
    
            
        def acqThreadLoop(self,expPeriod,NbFrames,acqQ,recvQ):
            
            framesLeft = NbFrames
            currFrame = 0
            while framesLeft > 0:
                try:
                    result = recvQ.get(timeout=0.001)
                except Queue.Empty:
                    pass
                else:
                    if result == "StopAcq":
                        acqQ.put("done")
                        return
                currFrame +=1
                framesLeft = NbFrames-currFrame
                acqQ.put(("currFrame",currFrame))
                time.sleep(expPeriod)
            acqQ.put("done")
            
        def StopAcq(self):
            self.recvQ.put("StopAcq")
            self.currState = "ON"
            self.currStatus = "Ready"
            self.acqThread = None
            