from flask import request
from flask_restful import Resource

import os
from datetime import datetime, timedelta

from utils import *


class SimulationData(Resource):
    def __init__(self):
        self.sim_folder_path = get_sim_folder_path()

    def get(self):
        """
        Get all building experiments for a resource
        :return: an array [created_time, experiment_name]
        """
        ret_val = []
        try:
            buildings = [bldg_name for bldg_name in os.listdir(self.sim_folder_path)
                         if os.path.isdir(os.path.join(self.sim_folder_path, bldg_name))]

            for bldg in buildings:
                sims = []
                bldg_sim_folder_path = os.path.join(self.sim_folder_path, bldg)
                simFolders = [sim_name for sim_name in os.listdir(bldg_sim_folder_path)
                              if os.path.isdir(os.path.join(bldg_sim_folder_path, sim_name))]
                for sim_name in simFolders:
                    created = os.path.getctime(os.path.join(bldg_sim_folder_path, sim_name))
                    created = datetime.utcfromtimestamp(created)
                    sims.append({
                        'name': sim_name,
                        'created': format_ts(created)
                    })

                ret_val.append({
                    'building': bldg,
                    'simulations': sims
                })
        except Exception as e:
            # logging
            print(e.message)

        return ret_val


if __name__ == '__main__':
    s = SimulationData()
    print(s.get())