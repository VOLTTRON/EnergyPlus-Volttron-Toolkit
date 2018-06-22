class AhuChiller(object):
    
    
    def __init__(self):
        self.tAirReturn = 20.
        self.tAirSupply = 10.
        self.tAirMixed = 20.
        self.cpAir = 1006. # J/kg
        self.c0 = 0 # coefficients are for SEB fan
        self.c1 = 2.652E-01
        self.c2 = -1.874E-02
        self.c3 = 1.448E-02
        self.c4 = 0.
        self.c5 = 0.
        self.pFan = 0.
        self.mDotAir = 0.
        self.staticPressure = 0.
        self.coilLoad = 0.
        self.COP = 6.16
        self.name = 'AhuChiller'
        
        
    def calcAirFlowRate(self, qLoad):
        if self.tAirSupply == self.tAirReturn:
            self.mDotAir = 0.0
        else:
            self.mDotAir = abs(qLoad/self.cpAir/(self.tAirSupply-self.tAirReturn)) # kg/s


    def calcFanPower(self):
        self.pFan = (self.c0 + self.c1*self.mDotAir + self.c2*pow(self.mDotAir,2) + self.c3*pow(self.mDotAir,3) + self.c4*self.staticPressure + self.c5*pow(self.staticPressure,2))*1000. # watts


    def calcCoilLoad(self):
        coilLoad = self.mDotAir*self.cpAir*(self.tAirSupply-self.tAirMixed) # watts
        if coilLoad > 0: #heating mode is not yet supported!
            self.coilLoad = 0.0
        else:
            self.coilLoad = coilLoad
        
        
    def calcTotalLoad(self, qLoad):
        self.calcAirFlowRate(qLoad)
        return self.calcTotalPower()
    
    
    def calcTotalPower(self):
        self.calcFanPower()
        self.calcCoilLoad()
        return abs(self.coilLoad)/self.COP/0.9 + self.pFan

