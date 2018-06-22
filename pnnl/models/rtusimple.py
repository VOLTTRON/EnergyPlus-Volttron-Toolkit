class RtuSimple(object):
    
    
    HEATING = 'heating'
    COOLING = 'cooling'
    CPAIR = 1006.0 #J/kg-K
    
    
    def __init__(self):
        # should be input to yield negative values?
        self.nominalCoolingCapacity = 10.0 #W
        self.nominalCoolingPower = 2.0 #W
        self.nominalHeatingCapacity = 10.0 #W
        self.nominalHeatingPower = 2.5 #W
        self.nominalFanPower = 0.5 #W
        self.nominalFlowRate = 1.0 #kg/s
        self.nominalAuxCapacity = 10.0 #W
        self.nominalAuxPower = 10.0 #W
        self.oaFraction = 0.4
        self.isCompressorRunning = True
        self.isFanRunning = True
        self.mode = RtuSimple.COOLING
        self.isAuxOn = False
        self.runTime = 0.0
        self.minRunTime = 0.0
        self.offTime = 0.0
        self.minOffTime = 0.0
        self.tIn = 22.0
        self.tOut = 24.0
        
    
    def calcCoolPower(self):
        return self.nominalCoolingPower
    
    
    def calcCoolCapacity(self):
        return -self.nominalCoolingCapacity
    
    
    def calcMinCoolCapacity(self, timeStep):
        onFraction = self.calcMinCoolRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcCoolCapacity()*onFraction + self.calcVentilationCapacity()*offFraction
    
    
    def calcMaxCoolCapacity(self, timeStep):
        onFraction = self.calcMaxCoolRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcCoolCapacity()*onFraction + self.calcVentilationCapacity()*offFraction
    
    
    # calculate the minimum power based on power * min run time
    def calcMinCoolPower(self, timeStep):
        onFraction = self.calcMinCoolRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcCoolPower()*onFraction + self.nominalFanPower*offFraction
    
    
    # calculate the maximum power based on power * max run time
    def calcMaxCoolPower(self, timeStep):
        onFraction = self.calcMaxCoolRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcCoolPower()*onFraction + self.nominalFanPower*offFraction
    
    
    def calcMinCoolRunFraction(self, timeStep):
        t = 0.0
        if self.isCompressorRunning and self.runTime < self.minRunTime:
            t = min(timeStep, self.minRunTime-self.runTime)
        return t/timeStep
        
        
    def calcMaxCoolRunFraction(self, timeStep):
        t = timeStep
        if not self.isCompressorRunning and self.offTime < self.minOffTime:
            t = min(timeStep, self.minOffTime-self.offTime)
        return t/timeStep
        
        
    def calcHeatPower(self):
        power = self.nominalHeatingPower
        if self.isAuxOn:
            power += self.nominalAuxPower
        return power
    
    
    def calcHeatCapacity(self):
        capacity = self.nominalHeatingCapacity
        if self.isAuxOn:
            capacity += self.nominalAuxCapacity
        return capacity
    
    
    def calcMinHeatCapacity(self, timeStep):
        onFraction = self.calcMinHeatRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcHeatPower()*onFraction + self.calcVentilationCapacity()*offFraction
    
    
    def calcMaxHeatCapacity(self, timeStep):
        onFraction = self.calcMaxHeatRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcHeatPower()*onFraction + self.calcVentilationCapacity()*offFraction
    
    
    # calculate the minimum power based on power * min run time
    def calcMinHeatPower(self, timeStep):
        onFraction = self.calcMinHeatRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcHeatPower()*onFraction + self.nominalFanPower*offFraction
    
    
    # calculate the maximum power based on power * max run time
    def calcMaxHeatPower(self, timeStep):
        onFraction = self.calcMaxHeatRunFraction(timeStep)
        offFraction = 1-onFraction
        return self.calcHeatPower()*onFraction + self.nominalFanPower*offFraction
    
    
    # this may use a different flag at some point
    def calcMinHeatRunFraction(self, timeStep):
        return self.calcMinCoolRunFraction(timeStep)
        
        
    # this may use a different flag at some point
    def calcMaxHeatRunFraction(self, timeStep):
        return self.calcMaxCoolRunFraction(timeStep)
    
    
    def calcVentilationCapacity(self):
        return self.nominalFlowRate*RtuSimple.CPAIR*(self.tIn-self.tOut)*self.oaFraction
