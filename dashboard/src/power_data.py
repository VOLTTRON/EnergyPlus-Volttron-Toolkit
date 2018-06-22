from flask import request
from flask_restful import Resource

import os
import sqlite3
import pytz
import traceback
from datetime import datetime
import pandas as pd
import numpy as np

from utils import *
from eplus_tmpl import EPlusTmpl


class PowerData(Resource):
    def __init__(self):
        self.sim_folder_path = get_sim_folder_path()
        self.local_tz = pytz.timezone('US/Pacific')
        self.delta_in_min = 60  # 15
        self.year = 2000

    def get(self):
        bldg = request.args.get('bldg')
        sim = request.args.get('sim')

        return self.get_data(bldg, sim)

    def get_data(self, bldg, sim):
        ret_val = []
        baseline_conn = None
        sim_conn = None

        try:
            # Query config data
            demand_limit = get_demand_limit(bldg, sim)

            # Query simulation data
            query = EPlusTmpl.get_power_point(bldg)
            df_sim = get_sim_data(bldg, sim, query, baseline=False)

            # E+ has hours from 1..24 so -1 before converting to datetime
            #df_sim['Hour'] = np.where(df_sim['Hour'] != 0, df_sim['Hour'] - 1, df_sim['Hour'])
            df_sim = df_sim[(df_sim['Hour'] >= 0) & (df_sim['Hour'] < 24)]
            df_sim.rename(columns={'value': 'power'}, inplace=True)

            # Create common column to join
            add_ts_col(df_sim)

            # Query baseline data
            df = df_sim
            df_baseline = get_sim_data(bldg, sim, query, baseline=True)
            if df_baseline is not None and not df_baseline.empty:
                df_baseline = df_baseline[(df_baseline['Hour'] >= 0) & (df_baseline['Hour'] < 24)]
                df_baseline.rename(columns={'value': 'baseline'}, inplace=True)
                add_ts_col(df_baseline)

                # Join dfs
                df = pd.merge(df_sim, df_baseline, how='left', on='ts')
            else:
                df['baseline'] = -9999

            # Filter needed columns
            df = df[['ts', 'baseline', 'power']]

            # Reformat ts column
            df['ts'] = df['ts'].dt.strftime('%Y-%m-%d %H:%M:%S')

            # Add zone_comfort column
            df['demand_limit'] = demand_limit

            # Drop nan
            df = df.dropna()

            # Convert to/from JSON to respond to client
            ret_val = df.to_json(orient='records')
            ret_val = json.loads(ret_val)

            # Use controllable load instead of whole building power for TCC
            if '_tcc' in bldg:
                power_file_path = get_power_file_path(bldg, sim)
                baseline_file_path = get_baseline_file_path(bldg, sim)
                if os.path.isfile(power_file_path):
                    with open(power_file_path, 'r') as f:
                        lines = f.read().splitlines()
                        for i in range(len(ret_val)):
                            ret_val[i]['power'] = float(lines[i])/1000.0
                if os.path.isfile(baseline_file_path):
                    with open(baseline_file_path, 'r') as f:
                        lines = f.read().splitlines()
                        for i in range(len(ret_val)):
                            ret_val[i]['baseline'] = float(lines[i])/1000.0

            # Average 30-minute for ILC. This assumes simulation is in 1-min time step
            if 'building1_ilc' in bldg or '_tcc' in bldg:
                self.avg_30min(ret_val)

        except Exception as e:
            traceback.print_exc()
            return ret_val

        return ret_val

    def avg_30min(self, ret_val):
        powers = []
        baselines = []
        window = 30

        for i in range(len(ret_val)):
            if i < window - 1:
                powers.append(ret_val[i]['power'])
                baselines.append(ret_val[i]['baseline'])
            else:
                if i > window - 1:
                    powers.pop(0)
                    baselines.pop(0)
                powers.append(ret_val[i]['power'])
                ret_val[i]['power'] = sum(powers) / window

                baselines.append(ret_val[i]['baseline'])
                ret_val[i]['baseline'] = sum(baselines) / window


if __name__ == '__main__':
    p = PowerData()
    print(p.get_data('building1_tcc_fp', 'simx'))
    #print(p.get_data('small_office_ilc', 'sim2'))
