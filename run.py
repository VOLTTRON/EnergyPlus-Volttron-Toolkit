import os
import subprocess
import time
from shutil import copyfile
import sys
import json,collections

if sys.argv[1].lower().find('b1')!=-1:
      configdir='/home/vuser/volttron/config/energyplus/building1/ep_building1_ilc.config'
else:
      configdir='/home/vuser/volttron/config/energyplus/small_office/ep_small_office_ilc.config'
with open(configdir) as f:
        config=json.load(f,object_pairs_hook=collections.OrderedDict)
        property=config['properties']
        model= property['model']
        weather= property['weather']
        bcvtb_home= property['bcvtb_home']

print model

modelPath = model
if (modelPath[0] == '~'):
            modelPath = os.path.expanduser(modelPath)
if (modelPath[0] != '/'):
            modelPath = os.path.join(self.cwd,modelPath)
weatherPath = weather
if (weatherPath[0] == '~'):
            weatherPath = os.path.expanduser(weatherPath)
if (weatherPath[0] != '/'):
            weatherPath = os.path.join(self.cwd,weatherPath)
modelDir = os.path.dirname(modelPath)
bcvtbDir = bcvtb_home
if (bcvtbDir[0] == '~'):
            bcvtbDir = os.path.expanduser(bcvtbDir)
if (bcvtbDir[0] != '/'):
            bcvtbDir = os.path.join(self.cwd,bcvtbDir)

print modelPath

print configdir

print modelDir

cmdStr = "cd %s; export BCVTB_HOME=\"%s\"; energyplus -w \"%s\" -r \"%s\"" % (modelDir, bcvtbDir, weatherPath, modelPath)

simulation = subprocess.Popen(cmdStr, shell=True)
sock=subprocess.Popen('python ' +str('/home/vuser/volttron/')+'master_nn.py'+' '+str(modelPath)+' '+str(configdir)+' '+str(modelDir), shell=True)


sock.wait()
#sock.terminate()
copyfile(modelDir+'/eplusout.sql', modelDir+'/baseline_eplusout.sql')
