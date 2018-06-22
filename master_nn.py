import socket
import time
import numpy as np
import sys
import random as rd
import json,collections
import pandas as pd

class socket_server:

    def __init__(self):     
          self.sock=socket.socket()
          self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          host=socket.gethostname()
          port=47569
          self.sock.bind(("127.0.0.1",port))
          self.sock.listen(10)
		  
def data_parse(data): 
    data=data.replace('[','')     
    data=data.replace(']','')  	
    data=data.split(',')

    for i in range(len(data)):
	              data[i]=float(data[i])
         
    return data

def read_data(file_name): 
    reg=np.loadtxt(file_name)
    reg_ref=[abs(number) for number in reg]
    reg=reg/max(reg_ref)
    return reg

	
def EP(model_path,startmonth,startday,endmonth,endday,timestep):

        f = open(model_path, 'r')
        lines = f.readlines()
        f.close()
		
        for i in range(len(lines)):
            if lines[i].lower().find('runperiod,') != -1:
                lines[i + 2] = '    ' + str(startmonth) + ',                       !- Begin Month' + '\n'
                lines[i + 3] = '    ' + str(startday) + ',                       !- Begin Day of Month' + '\n'
                lines[i + 4] = '    ' + str(endmonth) + ',                      !- End Month' + '\n'
                lines[i + 5] = '    ' + str(endday) + ',                      !- End Day of Month' + '\n'
            elif lines[i].lower().find('timestep,') != -1 and lines[i].lower().find('update frequency') == -1:
                if lines[i].lower().find(';') != -1:
                    lines[i] = '  Timestep,' + str(timestep) + ';' + '\n'
                else:
                    lines[i + 1] = '  ' + str(timestep) + ';' + '\n'                    
        f = open(model_path, 'w')
        for i in range(len(lines)):
            f.writelines(lines[i])
        f.close()	
	

def write_port_file(modeldir,port,host):
        fh = open(modeldir+'/socket.cfg', "w+")
        fh.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        fh.write('<BCVTB-client>\n')
        fh.write('  <ipc>\n')
        fh.write('    <socket port="%r" hostname="%s"/>\n' % (port, host))
        fh.write('  </ipc>\n')
        fh.write('</BCVTB-client>')
        fh.close()


def detectPowerData(config):
    with open(config) as f:
        power_index=[]
        convert_factor=[]		
        i=0
        config=json.load(f,object_pairs_hook=collections.OrderedDict)
        if 'outputs' in config:
            OUTPUTS = config['outputs']		
        for obj in OUTPUTS.itervalues():
            if obj.has_key('meta'):
                meta=obj.get('meta')
                
                if meta.get('units').lower().find('watts')!=-1:
                          power_index.append(i)
                          if obj.get('type').lower().find('district')!=-1:
                                       convert_factor.append(6.16)
                          else:
                                       convert_factor.append(1)						  
            i=i+1              		

    return power_index, convert_factor 


def writeVariableFile(config,modeldir):
    with open(config) as f:
        config=json.load(f,object_pairs_hook=collections.OrderedDict)
        if 'inputs' in config: 
            INPUTS = config['inputs']
        if 'outputs' in config:
            OUTPUTS = config['outputs']
        property=config['properties']
        timestep= property['timestep']
        startmonth= property['startmonth']
        startday= property['startday']
        endmonth= property['endmonth']
        endday= property['endday']
        ePlusOutputs=0
        ePlusInputs=0
        fh = open(modeldir+'/variables.cfg', "w+")
        fh.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        fh.write('<!DOCTYPE BCVTB-variables SYSTEM "variables.dtd">\n')
        fh.write('<BCVTB-variables>\n')
        for obj in OUTPUTS.itervalues():
            if obj.has_key('name') and obj.has_key('type'):
                ePlusOutputs = ePlusOutputs + 1
                fh.write('  <variable source="EnergyPlus">\n')
                fh.write('    <EnergyPlus name="%s" type="%s"/>\n' % (obj.get('name'), obj.get('type')))
                fh.write('  </variable>\n')
        for obj in INPUTS.itervalues():
            if obj.has_key('name') and obj.has_key('type'):
                ePlusInputs = ePlusInputs + 1
                fh.write('  <variable source="Ptolemy">\n')
                fh.write('    <EnergyPlus %s="%s"/>\n' % (obj.get('type'), obj.get('name')))
                fh.write('  </variable>\n')
        fh.write('</BCVTB-variables>\n')
        fh.close()
        return timestep,startmonth,startday,endmonth,endday,ePlusOutputs,ePlusInputs
        

	

model_path=sys.argv[1]
server=socket_server()
timestep,startmonth,startday,endmonth,endday,ePlusOutputs,ePlusInputs=writeVariableFile(sys.argv[2],sys.argv[3])
power_list,convert_factor=detectPowerData(sys.argv[2])
write_port_file(sys.argv[3],47569,'127.0.0.1')
EP(model_path,startmonth,startday,endmonth,endday,timestep)

vers = 2
flag = 0
num_tset=10
if model_path.lower().find('building')!=-1:
          num_tset=25
          
server.sock.listen(10)

conn,addr=server.sock.accept()
powers=[]
while 1:


### data received from dymola
         
         data = conn.recv(10240)
         power=0
		 
#         print('I just got a connection from ', addr)

         data = data.rstrip()

         arry = data.split()
         flagt = float(arry[1])
         if flagt==1:
                 conn.close()
                 f=open(sys.argv[3]+'/tccpower_baseline.csv','w+')
                 for i in range(len(powers)):
                          f.writelines(str(powers[i])+'\n')
                 f.close()
                 sys.exit()
         if len(arry)>6:
              time=float(arry[5])
              mssg = '%r %r %r 0 0 %r' % (vers, flag, ePlusInputs, time)
              for i in range(len(power_list)):
                       power=power+float(arry[5+1+int(power_list[i])])/convert_factor[i]
              powers.append(power)					   
              tset=float(arry[5+int(ePlusOutputs)])
              lightset=float(arry[5+int(ePlusOutputs)-int(num_tset)])              
#              print tset
#              print lightset              
              for i in range(num_tset):
                    mssg = mssg + ' ' + str(tset)
              for i in range(ePlusInputs-num_tset):
                    mssg = mssg + ' ' + str(lightset)                    

              mssg =  mssg+'\n'
              conn.send(mssg)


             

