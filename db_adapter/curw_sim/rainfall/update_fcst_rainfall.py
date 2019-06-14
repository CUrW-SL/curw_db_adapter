import traceback
from datetime import datetime, timedelta
from db_adapter.csv_utils import read_csv

from db_adapter.base import get_Pool, destroy_Pool
from db_adapter.constants import CURW_SIM_DATABASE, CURW_SIM_PASSWORD, CURW_SIM_USERNAME, CURW_SIM_PORT, CURW_SIM_HOST
from db_adapter.constants import CURW_FCST_DATABASE, CURW_FCST_PASSWORD, CURW_FCST_USERNAME, CURW_FCST_PORT, CURW_FCST_HOST
from db_adapter.curw_sim.grids import get_obs_to_d03_grid_mappings_for_rainfall
from db_adapter.curw_sim.timeseries import Timeseries as Sim_Timeseries
from db_adapter.curw_fcst.timeseries import Timeseries as Fcst_Timeseries
from db_adapter.curw_fcst.source import get_source_id
from db_adapter.logger import logger


# for bulk insertion for a given one grid interpolation method
def update_rainfall_fcsts(target_model, method, grid_interpolation, model, version):

    """
    Update rainfall forecasts for flo2d models
    :param target_model: target model for which input ins prepared
    :param method: value interpolation method
    :param grid_interpolation: grid interpolation method
    :param model: wrf forecast model name
    :param version: wrf forecast model version
    :return:
    """

    try:
        # Connect to the database
        curw_sim_pool = get_Pool(host=CURW_SIM_HOST, user=CURW_SIM_USERNAME, password=CURW_SIM_PASSWORD,
                port=CURW_SIM_PORT, db=CURW_SIM_DATABASE)

        curw_fcst_pool = get_Pool(host=CURW_FCST_HOST, user=CURW_FCST_USERNAME, password=CURW_FCST_PASSWORD,
                port=CURW_FCST_PORT, db=CURW_FCST_DATABASE)

        Sim_TS = Sim_Timeseries(pool=curw_sim_pool)
        Fcst_TS = Fcst_Timeseries(pool=curw_fcst_pool)

        active_obs_stations = read_csv('curw_active_rainfall_obs_stations.csv')
        obs_stations_dict = { }  # keys: obs station id , value: [run_name, name, latitude, longitude]

        for obs_index in range(len(active_obs_stations)):
            obs_stations_dict[active_obs_stations[obs_index][2]] = [active_obs_stations[obs_index][1],
                                                                    active_obs_stations[obs_index][3],
                                                                    active_obs_stations[obs_index][4],
                                                                    active_obs_stations[obs_index][5]]

        obs_d03_mapping = get_obs_to_d03_grid_mappings_for_rainfall(pool=curw_sim_pool, grid_interpolation=grid_interpolation)

        source_id = get_source_id(pool=curw_fcst_pool, model=model, version=version)

        for obs_id in obs_stations_dict.keys():
            meta_data = {
                    'latitude': float('%.6f' % float(obs_stations_dict.get(obs_id)[2])),
                    'longitude': float('%.6f' % float(obs_stations_dict.get(obs_id)[3])),
                    'model': target_model, 'method': method,
                    'grid_id': 'rainfall_{}_{}_{}'.format(obs_stations_dict.get(obs_id)[0],
                            obs_stations_dict.get(obs_id)[1], grid_interpolation)
                    }

            tms_id = Sim_TS.get_timeseries_id(grid_id=meta_data.get('grid_id'), method=meta_data.get('method'))

            if tms_id is None:
                tms_id = Sim_TS.generate_timeseries_id(meta_data=meta_data)
                meta_data['id'] = tms_id
                logger.info("Insert entry to run table with id={}".format(tms_id))
                Sim_TS.insert_run(meta_data=meta_data)

            obs_end = Sim_TS.get_obs_end(id_=tms_id)

            fcst_timeseries = []

            if obs_end is not None:
                fcst_timeseries = Fcst_TS.get_latest_timeseries(sim_tag="evening_18hrs",
                        station_id=obs_d03_mapping.get(meta_data['grid_id']), start=obs_end,
                        source_id=source_id, variable_id=1, unit_id=1)[1:]
            else:
                fcst_timeseries = Fcst_TS.get_latest_timeseries(sim_tag="evening_18hrs",
                        station_id=obs_d03_mapping.get(meta_data['grid_id']),
                        source_id=source_id, variable_id=1, unit_id=1)[1:]

            logger.info("Update forecast rainfall timeseries in curw_sim for id {}".format(tms_id))
            Sim_TS.insert_data(timeseries=fcst_timeseries, tms_id=tms_id, upsert=True)

    except Exception as e:
        traceback.print_exc()
        logger.error("Exception occurred while updating fcst rainfalls in curw_sim.")
    finally:
        destroy_Pool(curw_sim_pool)
        destroy_Pool(curw_fcst_pool)

