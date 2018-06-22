from rtusimple import RtuSimple


class RtuRegression(RtuSimple):
    
    
    def __init__(self):
        RtuSimple.__init__(self)
        # should be input to yield negative values?
        self.coolingCapacityCoeff = None
        self.coolingPowerCoeff = None
        self.heatingCapacityCoeff = None
        self.heatingPowerCoeff = None
        
        
    def calcCoolPower(self):
        power = self.nominalCoolingPower
        if self.coolingPowerCoeff is not None:
            c = self.coolingPowerCoeff
            power =  c[0] + c[1]*self.tOut + c[2]*self.tIn + c[3]*pow(self.tOut,2) + c[4]*pow(self.tIn,2) + c[5]*self.tOut*self.tIn
        return power
    
    
    def calcCoolCapacity(self):
        capacity = -self.nominalCoolingCapacity
        if self.coolingCapacityCoeff is not None:
            c = self.coolingCapacityCoeff
            capacity = -(c[0] + c[1]*self.tOut + c[2]*self.tIn + c[3]*pow(self.tOut,2) + c[4]*pow(self.tIn,2) + c[5]*self.tOut*self.tIn)
        return capacity
        
        
    def calcHeatPower(self):
        power = self.nominalHeatingPower
        if self.heatingPowerCoeff is not None:
            c = self.heatingPowerCoeff
            power = c[0] + c[1]*self.tOut + c[2]*self.tIn + c[3]*pow(self.tOut,2) + c[4]*pow(self.tIn,2) + c[5]*self.tOut*self.tIn
        if self.isAuxOn:
            power += self.nominalAuxPower
        return power
    
    
    def calcHeatCapacity(self):
        capacity = self.nominalHeatingCapacity
        if self.heatingCapacityCoeff is not None:
            c = self.heatingCapacityCoeff
            capacity = (c[0] + c[1]*self.tOut + c[2]*self.tIn + c[3]*pow(self.tOut,2) + c[4]*pow(self.tIn,2) + c[5]*self.tOut*self.tIn)
        if self.isAuxOn:
            capacity += self.nominalAuxCapacity
        return capacity
        
        