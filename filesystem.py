import os
import time

class Filesystem:

    FS_ROOT_NONE = 0
    FS_ROOT_PILATUS = 1
    FS_ROOT_LOCAL = 2
    FS_ROOT_REMOTE = 3
    FS_SUB_RAW = 0
    FS_SUB_PROCESSED = 4
    FS_SUB_SHARED = 8
    FS_SUB_SCRATCH = 12
    FS_TYPE_REGULAR = 0
    FS_TYPE_SCREENING = 16
    FS_TYPE_SCAN = 32
    FS_TYPE_CUSTOM = 48
    FS_MASK_ROOT = 3
    FS_MASK_SUB = 12
    FS_MASK_TYPE = 48
    
    commissioning = False
    fallback = False
    runnumber = 1
    posnumber = 1
    types = ("", "screening", "scan", "")
    beamtime = 0
    tag = "test"
    user = ""
    sample = "/test"
    cache = {}

    prefixPilatus = "/ramdisk"
    prefixLocal = "/gpfs"
    prefixRemote = "/asap3/petra3/gpfs/p11"
    interfixFallback = "/local"
    interfixBeamtime = "/current"
    interfixCommissioning = "/commissioning"
    suffixRaw = "/raw"
    suffixProcessed = "/processed"
    suffixShared = "/shared"
    suffixScratch = "/scratch"
    suffixScratchLocal = "/scratch_bl"
    suffixScratchRemote = "/scratch_cc"


    def __init__(self):
        self.prefixRemote += "/" + time.strftime("%Y")


    def getPath(self, pathType=None, force=False):
        path = ""
        if pathType is None:
            pathType = self.FS_ROOT_LOCAL
        if pathType + 1 <= self.FS_MASK_TYPE and self.cache.has_key(pathType):
            if(force):
                return self.checkPath(self.cache[pathType], force)
            return self.cache[pathType]
        #pre and interfix
        root = pathType & self.FS_MASK_ROOT
        if root == self.FS_ROOT_NONE:
            pass
        elif root == self.FS_ROOT_PILATUS:
            path += self.prefixPilatus
            if self.commissioning:
                path += self.interfixCommissioning
            elif self.fallback:
                path += self.interfixFallback
            else:
                path += self.interfixBeamtime
        elif self.fallback:
            path += self.prefixLocal + self.interfixFallback
        elif root == self.FS_ROOT_LOCAL:
            path += self.prefixLocal
            if self.commissioning:
                path += self.interfixCommissioning
            else:
                path += self.interfixBeamtime
        else:
            path += self.prefixRemote
            if self.commissioning:
                path += "/" + self.tag
            else:
                path += "/%08d"%self.beamtime
        #suffix
        sub = pathType & self.FS_MASK_SUB
        if sub == self.FS_SUB_RAW:
            path += self.suffixRaw
        elif sub == self.FS_SUB_PROCESSED:
            path += self.suffixProcessed
        elif sub == self.FS_SUB_SHARED:
            path += self.suffixShared
        elif sub == self.FS_SUB_SCRATCH:
            if(root == self.FS_ROOT_LOCAL):
                path += self.suffixScratchLocal
            if(root == self.FS_ROOT_REMOTE):
                path += self.suffixScratchRemote
            else:
                path += self.suffixScratch
        #user
        if self.user != "":
            path += self.user
        #sample
        type = pathType & self.FS_MASK_TYPE
        path += self.sample + self.sample
        if self.types[type/16] != "":
            path += "_" + self.types[type/16]
        path += "_%03d"%self.runnumber
        if type == self.FS_TYPE_SCAN:
            path += "/P%06d"%self.posnumber
        if type != self.FS_TYPE_CUSTOM:
            self.cache[pathType] = path
        if(force and root != self.FS_ROOT_NONE and root != self.FS_ROOT_PILATUS):
            return self.checkPath(path, force)
        return path


    def getFilename(self, type=None, suffix="00001.cbf"):
        if type is None:
            type = self.FS_TYPE_REGULAR
        type = type & self.FS_MASK_TYPE
        name = self.sample.lstrip("/")
        if self.types[type/16] != "":
            name += "_" + self.types[type/16]
        name += "_%03d"%self.runnumber
        if type == self.FS_TYPE_SCAN:
            name += "_P%06d"%self.posnumber
        name += "_"
        name += str(suffix)
        return name


    def setSample(self, sample):
        sample = str(sample).replace("\\", "/")
        dirs = sample.lstrip("/").split("/")
        sample = ""
        for d in dirs:
            if(d.find("*") > -1 or d.find("?") > -1 or d.find("..") > -1):
                return False
            sample += "/" + d
        if(sample != self.sample):
            self.sample = sample
            self.cache = {}
        return True


    def setCustom(self, custom):
        custom = str(custom)
        types[4] = custom

        
    def setRunnumber(self, n, pathType=None):
        tempRunnumber = self.runnumber
        tempCache = self.cache
        revert = False
        self.runnumber = int(n)
        self.cache = {}
        #check
        if type(pathType) is int:
            path = self.getPath(pathType, False)
            if type(path) is not str:
                revert = True
            file = self.getFilename(pathType)
            if type(file) is not str:
                revert = True
            if self.checkFileExistence(path + "/" + file):
                revert = True
            if revert:
                self.runnumber = tempRunnumber
                self.cache = tempCache
                return False
            if self.runnumber == tempRunnumber:
                self.cache = tempCache
            return True


    def setPosnumber(self, n, pathType=None):
        tempPosnumber = self.posnumber
        tempCache = self.cache
        revert = False
        self.posnumber = int(n)
        self.cache = {}
        #check
        if type(pathType) is int:
            path = self.getPath(pathType, False)
            if type(path) is not str:
                revert = True
            file = self.getFilename(pathType)
            if type(file) is not str:
                revert = True
            if self.checkFileExistence(path + "/" + file):
                revert = True
            if revert:
                self.posnumber = tempPosnumber
                self.cache = tempCache
                return False
            if self.posnumber == tempPosnumber:
                self.cache = tempCache
            return True
        else:
            return True
            

    def incRunnumber(self, pathType=None):
        n = self.runnumber
        if n == 0 or n == 1:
            if self.setRunnumber(1, pathType):
                return True
        while n < 1000:
            n += 1
            if self.setRunnumber(n, pathType):
                return True
        return False


    def incPosnumber(self, pathType=None):
        n = self.posnumber
        if n == 0 or n == 1:
            if self.setPosnumber(1, pathType):
                return True
        while n < 1000:
            n += 1
            if self.setPosnumber(n, pathType):
                return True
        return False


    def setFallback(self, fallback):
        if bool(fallback) != self.fallback:
            self.fallback = bool(fallback)
            self.cache = {}

    
    def setCommissioning(self, commissioning):
        if type(commissioning) is str:
            if self.commissioning != True or self.tag != commissioning:
                self.tag = commissioning
                self.commissioning = True
                self.cache = {}
        elif self.commissioning != bool(commissioning):
            self.commissioning = bool(commissioning)
            self.cache = {}

    
    def setBeamtime(self, beamtime):
        if int(beamtime) != self.beamtime:
            self.beamtime = int(beamtime)
            self.cache = {}

    
    def setUser(self, user):
        user = str(user).replace("\\", "/")
        dirs = user.lstrip("/").split("/")
        user = ""
        for d in dirs:
            if(d.find("*") > -1 or d.find("?") > -1 or d.find("..") > -1):
                return False
            user += "/" + d
        if user != self.user:
            self.user = user
            self.cache = {}
        return True


    def getLastRunnumber(self, pathType=None):
        tempRunnumber = self.runnumber
        tempPosnumber = self.posnumber
        self.setPosnumber(1, False)
        for run in range(1, 9999):
            self.setRunnumber(run, False)
            path = self.getPath(pathType, False)
            if type(path) is not str:
                return False
            file = self.getFilename(pathType)
            if type(file) is not str:
                return False
            if not self.checkFileExistence(path + "/" + file):
                return run - 1
        self.setPosnumber(tempPosnumber, False)
        self.setRunnumber(tempRunnumber, False)
        return False
            

    def getLastPosnumber(self, pathType=None):
        tempPosnumber = self.posnumber
        for pos in range(1, 999999):
            self.setPosnumber(pos, False)
            path = self.getPath(pathType, False)
            if type(path) is not str:
                return False
            file = self.getFilename(pathType)
            if type(file) is not str:
                return False
            if not self.checkFileExistence(path + "/" + file):
                return pos - 1
        self.setPosnumber(tempPosnumber, False)
        return False
            

    def checkPath(self, path=None, force=False):
        path = str(path).replace("\\", "/")
        dirs = path.lstrip("/").split("/")
        path = ""
        for d in dirs:
            if(d.find("*") > -1 or d.find("?") > -1 or d.find("..") > -1):
                return False
            path += "/" + d
            if(not os.access(path, os.F_OK)):
                if(force):
                    try:
                        os.mkdir(path)
                    except:
                        return False
                else:
                    return False
        if(not os.access(path, os.W_OK)):
            return False
        return path


    def checkFileExistence(self, path, mode=os.F_OK):
        return os.access(path, mode)


    def writeFile(self, path, content):
        try:
            f = os.open(path, os.O_RDWR|os.O_CREAT)
            os.write(f, content)
            os.close(f)
            return True
        except:
            return False
        
    
    def checkDiskSpace(self, path):
        try:
            stat = os.statvfs(path)
        except:
            return -1
        return (stat.f_bavail * stat.f_frsize) / 1048576. #in MByte

