import json,collections

def detectPowerData(config):
    with open(config) as f:
        power_index=[]
        i=0
        config=json.load(f,object_pairs_hook=collections.OrderedDict)
        if 'outputs' in config:
            OUTPUTS = config['outputs']		
        for obj in OUTPUTS.itervalues():
            if obj.has_key('meta'):
                meta=obj.get('meta')
                
                if meta.get('units').lower().find('watts')!=-1:
                          power_index.append(i)
            i=i+1              		
        print meta
    return power_index 

print detectPowerData('ep_building1_ilc.config') 