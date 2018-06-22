class FirstOrderZone(object):
    
    
    def __init__(self):
        self.c0 = 0.3557725
        self.c1 = 0.9837171
        self.c2 = 0.002584267
        self.c3 = 0.0006142672
        self.c4 = 0.0006142672
        self.x0 = -162.6386
        self.x1 = -309.5303
        self.x2 = -4.800622
        self.x3 = 321.3943
        self.x4 = 0.9944429
        self.tOut = 20.
        self.tIn = 24.
        self.tSet = 21.11
        self.tDel = 0.25
        self.qHvacSens = 0.
        self.tMin = 22.
        self.tMax = 24.
        self.qMin = -1.
        self.qMax = -1000000.
        self.name = "FirstOrderZone"


    def getQ(self, T_new):
        qHvacNew = self.x0 + self.x1*self.tIn + self.x2*self.tOut + self.x3*T_new + self.x4*self.qHvacSens
        return qHvacNew
    
    
    def calcMinCoolPower(self):
        # q values are negative, so this is confusing
        t = max(min((self.tSet+self.tDel), self.tMax), self.tMin)
        q = max(min(self.getQ(t), self.qMin), self.qMax)
        return q


    def calcMaxCoolPower(self):
        # q values are negative, so this is confusing
        t = min(max((self.tSet-self.tDel), self.tMin), self.tMax)
        q = max(min(self.getQ(t), self.qMin), self.qMax)
        return q


    def getT(self, qHvac):
       return self.c0 + self.c1*self.tIn + self.c2*self.tOut + self.c3*qHvac + self.c4*self.qHvacSens

#    def getT(self, qHvac):
#        return (self.x0 + self.x1*self.tIn + self.x2*self.tOut +  + self.x4*self.qHvacSens- qHvac)/self.x3

