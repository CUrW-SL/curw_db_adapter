import traceback
import pymysql
from datetime import datetime, timedelta

from db_adapter.csv_utils import read_csv
from db_adapter.base import get_Pool, destroy_Pool
from db_adapter.constants import CURW_SIM_DATABASE, CURW_SIM_PASSWORD, CURW_SIM_USERNAME, CURW_SIM_PORT, CURW_SIM_HOST
from db_adapter.constants import HOST, PASSWORD, PORT, DATABASE, USERNAME
from db_adapter.curw_sim.timeseries import Timeseries
from db_adapter.curw_sim.common import process_5_min_ts
from db_adapter.logger import logger


def extract_rain_ts(connection, id, start_time):
    """
    Extract obs station timeseries (15 min intervals)
    :param connection: connection to curw database
    :param stations_dict: dictionary with station_id as keys and run_ids as values
    :param start_time: start of timeseries
    :return:
    """

    timeseries = []

    try:
        # Extract per 5 min observed timeseries
        with connection.cursor() as cursor1:
            sql_statement = "select `time`, `value`  from data where `id`=%s and `time` >= %s ;"
            print(id, start_time)
            rows = cursor1.execute(sql_statement, (id, start_time))
            if rows > 0:
                results = cursor1.fetchall()
                for result in results:
                    timeseries.append([result.get('time'), result.get('value')])
        if len(timeseries) > 1:
            print(id, "::", len(timeseries), "::", timeseries[1][0], "::", timeseries[-1][0])
        return timeseries

    except Exception as ex:
        traceback.print_exc()
    # finally:
    #     if connection is not None:
    #         connection.close()


# for bulk insertion for a given one grid interpolation method
def update_rainfall_obs(target_model, method, grid_interpolation):

    """
    Update rainfall observations for flo2d models
    :param model: target model
    :param method: value interpolation method
    :param grid_interpolation: grid interpolation method
    :return:
    """

    now = datetime.now()
    OBS_START_STRING = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:00:00')
    OBS_START = datetime.strptime(OBS_START_STRING, '%Y-%m-%d %H:%M:%S')
    print(OBS_START, type(OBS_START))

    try:

        # Connect to the database
        curw_connection = pymysql.connect(host='104.198.0.87',
                user='root',
                password='cfcwm07',
                db='curw',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor)

        # pool = get_Pool(host=CURW_SIM_HOST, user=CURW_SIM_USERNAME, password=CURW_SIM_PASSWORD,
        #         port=CURW_SIM_PORT, db=CURW_SIM_DATABASE)

        ##test ######
        pool = get_Pool(host=HOST, user=USERNAME, password=PASSWORD, port=PORT, db=DATABASE)

        TS = Timeseries(pool=pool)

        active_obs_stations = read_csv('curw_active_rainfall_obs_stations.csv')
        obs_stations_dict = { }  # keys: obs station id , value: [hash id, run_name, name,latitude, longitude]

        for obs_index in range(len(active_obs_stations)):
            obs_stations_dict[active_obs_stations[obs_index][2]] = [active_obs_stations[obs_index][0],
                                                                    active_obs_stations[obs_index][1],
                                                                    active_obs_stations[obs_index][3],
                                                                    active_obs_stations[obs_index][4],
                                                                    active_obs_stations[obs_index][5]]

        for obs_id in obs_stations_dict.keys():
            obs_start = OBS_START
            meta_data = {
                    'latitude': float('%.6f' % float(obs_stations_dict.get(obs_id)[3])),
                    'longitude': float('%.6f' % float(obs_stations_dict.get(obs_id)[4])),
                    'model': target_model, 'method': method,
                    'grid_id': 'rainfall_{}_{}_{}'.format(obs_stations_dict.get(obs_id)[1],
                            obs_stations_dict.get(obs_id)[2], grid_interpolation)
                    }

            tms_id = TS.get_timeseries_id(grid_id=meta_data.get('grid_id'), method=meta_data.get('method'))

            if tms_id is None:
                tms_id = TS.generate_timeseries_id(meta_data=meta_data)
                meta_data['id'] = tms_id
                logger.info("Insert entry to run table with id={}".format(tms_id))
                TS.insert_run(meta_data=meta_data)

            obs_end = TS.get_obs_end(id_=tms_id)

            if obs_end is not None:
                obs_start = obs_end

            obs_hash_id = obs_stations_dict.get(obs_id)[0]

            obs_timeseries = []

            ts = extract_rain_ts(connection=curw_connection, start_time=obs_start, id=obs_hash_id)
            if ts is not None and len(ts) > 1:
                obs_timeseries.extend(process_5_min_ts(newly_extracted_timeseries=ts, expected_start=obs_start)[1:])
                # obs_start = ts[-1][0]

            for i in range(len(obs_timeseries)):
                if obs_timeseries[i][1] == -99999:
                    obs_timeseries[i][1] = 0

            logger.info("Update observed rainfall timeseries in curw_sim for id {}".format(tms_id))
            TS.insert_data(timeseries=obs_timeseries, tms_id=tms_id, upsert=True)

            if obs_timeseries is not None and len(obs_timeseries) > 0:
                logger.info("Update latest obs {}".format(obs_timeseries[-1][1]))
                TS.update_latest_obs(id_=tms_id, obs_end=(obs_timeseries[-1][1]))

    except Exception as e:
        traceback.print_exc()
        logger.error("Exception occurred while updating obs rainfalls in curw_sim.")
    finally:
        destroy_Pool(pool=pool)