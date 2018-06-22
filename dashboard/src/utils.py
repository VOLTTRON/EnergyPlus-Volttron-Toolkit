import os
import json


def format_ts(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_sim_folder_path():
    return '/Users/ngoh511/Documents/projects/PycharmProjects/volttron_ep_toolkit/dashboard/src/simulations'
    #return '/home/vuser/volttron/simulations/'


def get_sim_file_path(bldg, sim, baseline=False):
    file = "baseline_eplusout.sql" if baseline else "eplusout.sql"
    return os.path.join(get_sim_folder_path(), bldg, sim, file)


def get_power_file_path(bldg, sim):
    return os.path.join(get_sim_folder_path(), bldg, sim, 'tccpower.csv')


def get_baseline_file_path(bldg, sim):
    return os.path.join(get_sim_folder_path(), bldg, sim, 'tccpower_baseline.csv')


def get_ilc_config_path(bldg, sim):
    name = ''
    path = ''
    if 'small_office' in bldg:
        name = 'so_ilc_config'
    elif 'medium_office' in bldg:
        name = 'mo_ilc_config'
    elif 'large_office' in bldg:
        name = 'lo_ilc_config'
    elif 'building1' in bldg:
        name = 'b1_ilc_config'

    if name != '':
        path = os.path.join(get_sim_folder_path(), bldg, sim, name)

    return path


def get_tcc_fd_config_path(bldg, sim):
    name = 'meter-config-fixed-demand'
    path = os.path.join(get_sim_folder_path(), bldg, sim, name)

    return path


def get_tcc_config_path(bldg, sim, zone):
    return os.path.join(get_sim_folder_path(), bldg, sim, zone+'-config')


def get_demand_limit(bldg, sim):
    demand_limit = -9999

    if not 'tcc_fp' in bldg:
        try:
            path = get_ilc_config_path(bldg, sim)
            point = 'demand_limit'
            if 'tcc_fd' in bldg:  # fixed_demand
                path = get_tcc_fd_config_path(bldg, sim)
                point = 'demand_limit_threshold'

            if os.path.isfile(path):
                with open(path, 'r') as fh:
                    config = json.load(fh)
                    if point in config:
                        demand_limit = float(config[point])/1000.0

        except Exception as e:
            print(e.message)

    return demand_limit


def get_tcc_comfort(bldg, sim, zone):
    low_limit = -9999
    high_limit = -9999
    path = get_tcc_config_path(bldg, sim, zone)

    try:
        if os.path.isfile(path):
            with open(path, 'r') as fh:
                config = json.load(fh)
                low_limit = float(config['tMin'])*1.8+32
                high_limit = float(config['tMax'])*1.8+32

    except Exception as e:
        print(e.message)

    return low_limit, high_limit


def get_sim_data(bldg, sim, query, baseline=False, year=2000):
    import sqlite3
    import pandas as pd
    import traceback

    df = None
    sim_path = get_sim_file_path(bldg, sim, baseline=baseline)
    if os.path.isfile(sim_path):
        try:
            conn = sqlite3.connect(sim_path)
            df = pd.read_sql_query(query, conn)
            df = add_ts_col(df, year)
        except Exception as e:
            traceback.print_exc()
        finally:
            conn.close()

    return df


def add_ts_col(df, year=None):
    import pandas as pd
    import pytz
    import datetime
    local_tz = pytz.timezone('US/Pacific')

    if year is None:
        year = datetime.datetime.utcnow().year

    df['Year'] = year
    df['ts'] = pd.to_datetime(df[['Year', 'Month', 'Day', 'Hour', 'Minute']])

    return df


if __name__ == '__main__':
    bldg = 'building1_tcc_fd'
    sim = 'simx'

    dl = get_demand_limit(bldg, sim)
    print(dl)
