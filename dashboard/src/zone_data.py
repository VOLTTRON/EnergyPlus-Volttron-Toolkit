from flask import request
from flask_restful import Resource

import os
import json
import pytz
import sqlite3
import pandas as pd

from utils import *
from eplus_tmpl import EPlusTmpl


class ZoneData(Resource):
    def __init__(self):
        self.sim_folder_path = get_sim_folder_path()

    def get(self, resource_id):
        """
        Get zone data
        :param resource_id: 1: all zones ---- 2: a specific zone
        :return:
        """
        ret_val = []

        bldg = request.args.get('bldg')
        sim = request.args.get('sim')

        # Get all zones
        if resource_id == 1:
            ret_val = self.get_all_zones(bldg, sim)

        # Get zone data
        elif resource_id == 2:
            zone_name = request.args.get('zone')
            ret_val = self.get_data(bldg, sim, zone_name)

        return ret_val

    def get_all_zones(self, bldg, sim):
        ret_val = []
        sim_path = get_sim_file_path(bldg, sim)
        if os.path.isfile(sim_path):
            try:
                # Open connection
                conn = sqlite3.connect(sim_path)
                c = conn.cursor()

                # Query
                c.execute(EPlusTmpl.zones_tmpl)
                rows = c.fetchall()
                for row in rows:
                    ret_val.append(row[0])
            except Exception as e:
                # logging
                print(e.message)
            finally:
                # Close connection
                conn.close()

        return ret_val

    def get_data(self, bldg, sim, zone_name):
        ret_val = []

        sim_path = get_sim_file_path(bldg, sim)
        if os.path.isfile(sim_path):
            try:
                # Open connection
                conn = sqlite3.connect(sim_path)

                # Get zone comfort level
                low_limit, high_limit = get_tcc_comfort(bldg, sim, zone_name)

                # Query data to dfs
                temp_point_query = EPlusTmpl.get_zone_temp_query(bldg, zone_name, 'temp')
                clg_sp_query = EPlusTmpl.get_zone_cooling_sp_query(bldg, zone_name, 'clg_sp')
                #htg_sp_query = EPlusTmpl.get_zone_heating_sp_query(bldg, zone_name, 'htg_sp')

                df_temp = get_sim_data(bldg, sim, temp_point_query)
                add_ts_col(df_temp)
                df = df_temp

                df_clg_sp = get_sim_data(bldg, sim, clg_sp_query)
                #df_htg_sp = get_sim_data(bldg, sim, htg_sp_query)

                if df_clg_sp is not None and not df_clg_sp.empty:
                    add_ts_col(df_clg_sp)
                    df = pd.merge(df_temp, df_clg_sp, how='left', on='ts')
                else:
                    df['clg_sp'] = -9999

                # Filter needed columns
                # df = df[['ts', 'temp', 'clg_sp', 'htg_sp']]
                df = df[['ts', 'temp', 'clg_sp']]

                # Reformat ts column
                df['ts'] = df['ts'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # Add zone_comfort column
                df['low_limit'] = low_limit
                df['high_limit'] = high_limit

                # Drop nan
                df = df.dropna()

                # Convert to/from JSON to respond to client
                ret_val = df.to_json(orient='records')
                ret_val = json.loads(ret_val)

            except Exception as e:
                # logging
                print(e.message)

            finally:
                # Close connection
                conn.close()

        return ret_val


if __name__ == '__main__':
    p = ZoneData()
    #print(p.get_data('small_office', 'sim2', 'SOUTH PERIM SPC GS1'))
    print(p.get_data('building1_tcc_fd', 'simx', 'ZONE-VAV-143'))
