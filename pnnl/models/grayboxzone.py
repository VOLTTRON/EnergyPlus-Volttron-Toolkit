from pyfmi import load_fmu
import numpy as np

from volttron.platform.agent import utils
import logging

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"

class GrayBoxZone(object):
    def __init__(self, modelname):
        self.tOut = 20.
        self.tIn = 24.
        self.qHvacSens = 0.
        self.tMin = 22.
        self.tMax = 24.
        self.qMin = -1.
        self.qMax = -1000000.
        self.c = 4000000
        self.r = 0.002
        self.shgc = 0.5
        self.modelName = "TestModels_MPC_R1C1HeatCool.fmu"

    def create_model(self):
        _log.debug("Create model: {} - C: {} - R: {} - SHGC: {}".format(self.modelName, self.c, self.r, self.shgc))
        self.model = load_fmu(self.modelName)
        self.model.set('C', self.c)
        self.model.set('R', self.r)
        self.model.set('shgc', self.shgc)

    def prepareInput(self, q):
        tout = [self.tOut]*6
        qsol = [0]*6
        qarr = [q]*6
        timearr = np.arange(0,360,60.)
        t_meas = timearr
        u = np.transpose([np.asarray(timearr).flatten(),
                          np.asarray(qsol).flatten(),
                          np.asarray(tout).flatten(),
                          np.asarray(qarr).flatten()])
        return u

    def getQ(self, T_new):   

        if T_new > self.tIn:
            q = self.qMin
        else:
            q = self.qMax
        input = self.prepareInput(q)
        self.create_model()
        self.model.set('T0', self.tIn)
        res = self.model.simulate(input=(['QHeaCoo', 'weaTDryBul', 'weaHGloHor'], input), start_time=0, final_time=360)
        while res['Tzone'][-1] > T_new and q >= self.qMin-abs(self.qMax -self.qMin)/10:
            q = q + abs(self.qMax - self.qMin)/10
            self.create_model()
            self.model.set('T0', self.tIn)
            input = self.prepareInput(q)			
            res = self.model.simulate(input=(['QHeaCoo','weaTDryBul','weaHGloHor'], input), start_time=0, final_time=360)
        return q

    def getT(self, qHvac):
        self.create_model()
        input = self.prepareInput(qHvac)
        self.model.set('T0', self.tIn)
        res = self.model.simulate(input=(['QHeaCoo','weaTDryBul','weaHGloHor'], input), start_time=0, final_time=360)
        return res['Tzone'][-1]


