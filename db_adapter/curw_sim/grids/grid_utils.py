import traceback
import csv
import pkg_resources

from db_adapter.logger import logger
from db_adapter.exceptions import DatabaseAdapterError


def add_flo2d_grid_mappings(pool, grid_interpolation, flo2d_model):

    """
    Add flo2d grid mappings to the database
    :param pool:  database connection pool
    :param grid_interpolation: grid interpolation method
    :param flo2d_model: string: flo2d model (e.g. FLO2D_250, FLO2D_150, FLO2D_30)
    :return: True if the insertion is successful, else False
    """

    with open('{}_{}_d03_stations_mapping.csv'.format(grid_interpolation, flo2d_model), 'r') as f1:
        flo2d_d03_mapping=[line for line in csv.reader(f1)][1:]

    with open('{}_{}_obs_mapping.csv'.format(grid_interpolation, flo2d_model), 'r') as f2:
        flo2d_obs_mapping=[line for line in csv.reader(f2)][1:]

    grid_mappings_list = []

    for index in range(len(flo2d_obs_mapping)):
        grid_mapping = ['{}_{}_{}'.format(flo2d_model, flo2d_obs_mapping[index][0], grid_interpolation), flo2d_obs_mapping[index][1],
                        flo2d_obs_mapping[index][3], flo2d_obs_mapping[index][5], flo2d_d03_mapping[index][1]]
        grid_mappings_list.append(tuple(grid_mapping))

    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            sql_statement = "INSERT INTO `grid_map` (`grid_id`, `obs1`, `obs2`, `obs3`, `fcst`)" \
                            " VALUES ( %s, %s, %s, %s, %s) "\
                            "ON DUPLICATE KEY UPDATE `obs1`=VALUES(`obs1`), `obs2`=VALUES(`obs2`), " \
                            "`obs3`=VALUES(`obs3`);"
            row_count = cursor.executemany(sql_statement, grid_mappings_list)
        connection.commit()
        return row_count
    except Exception as ex:
        connection.rollback()
        error_message = "Insertion of flo2d grid mappings failed."
        logger.error(error_message)
        traceback.print_exc()
        raise DatabaseAdapterError(error_message, ex)
    finally:
        if connection is not None:
            connection.close()


def get_flo2d_to_obs_grid_mappings(pool, grid_interpolation, flo2d_model):

    """
    Retrieve flo2d to obs grid mappings
    :param pool: database connection pool
    :param grid_interpolation: grid interpolation method
    :param flo2d_model: string: flo2d model (e.g. FLO2D_250, FLO2D_150, FLO2D_30)
    :return: dictionary with grid ids as keys and corresponding obs1, obs2, obs3 station ids as a list
    """

    flo2d_grid_mappings = {}

    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            sql_statement = "SELECT * FROM `grid_map` WHERE `grid_id` like %s ESCAPE '$'"
            row_count = cursor.execute(sql_statement, "flo2d$_{}$_%$_{}".format(flo2d_model.split('_')[1], grid_interpolation))
            if row_count > 0:
                results = cursor.fetchall()
                for dict in results:
                    flo2d_grid_mappings[dict.get("grid_id")] = [dict.get("obs1"), dict.get("obs2"), dict.get("obs3")]
                return flo2d_grid_mappings
            else:
                return None
    except Exception as ex:
        error_message = "Retrieving flo2d to obs grid mappings failed"
        logger.error(error_message)
        traceback.print_exc()
        raise DatabaseAdapterError(error_message, ex)
    finally:
        if connection is not None:
            connection.close()


def get_flo2d_to_wrf_grid_mappings(pool, grid_interpolation, flo2d_model):

    """
    Retrieve flo2d to wrf stations mappings
    :param pool: database connection pool
    :param grid_interpolation: grid interpolation method
    :param flo2d_model: string: flo2d model (e.g. FLO2D_250, FLO2D_150, FLO2D_30)
    :return: dictionary with grid ids as keys and corresponding wrf station ids as values
    """

    flo2d_grid_mappings = {}

    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            sql_statement = "SELECT `grid_id`, `fcst` FROM `grid_map` WHERE `grid_id` like %s ESCAPE '$'"
            row_count = cursor.execute(sql_statement, "flo2d$_{}$_%$_{}".format(flo2d_model.split('_')[1], grid_interpolation))
            if row_count > 0:
                results = cursor.fetchall()
                for dict in results:
                    flo2d_grid_mappings[dict.get("grid_id")] = dict.get("fcst")
                return flo2d_grid_mappings
            else:
                return None
    except Exception as ex:
        error_message = "Retrieving flo2d to obs grid mappings failed"
        logger.error(error_message)
        traceback.print_exc()
        raise DatabaseAdapterError(error_message, ex)
    finally:
        if connection is not None:
            connection.close()


def add_obs_to_d03_grid_mappings_for_rainfall(pool, grid_interpolation):

    """
    Add observational stations grid mappings to the database
    :param pool:  database connection pool
    :param grid_interpolation: grid interpolation method
    :return: True if the insertion is successful, else False
    """

    with open('{}_obs_d03_stations_mapping.csv'.format(grid_interpolation), 'r') as f1:
        obs_d03_mapping=[line for line in csv.reader(f1)][1:]

    with open('curw_active_rainfall_obs_stations.csv', 'r') as f2:
        obs_stations=[line for line in csv.reader(f2)][1:]

    obs_dict = {}

    for i in range(len(obs_stations)):
        obs_dict[obs_stations[i][2]] = [obs_stations[i][1], obs_stations[i][3]]

    grid_mappings_list = []

    for index in range(len(obs_d03_mapping)):
        grid_mapping = ['rainfall_{}_{}_{}'.format(obs_dict.get(obs_d03_mapping[index][0])[0], obs_dict.get(obs_d03_mapping[index][0])[1], grid_interpolation),
                        obs_d03_mapping[index][1], obs_d03_mapping[index][3], obs_d03_mapping[index][5]]
        grid_mappings_list.append(tuple(grid_mapping))

    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            sql_statement = "INSERT INTO `grid_map_obs` (`grid_id`, `d03_1`, `d03_2`, `d03_3`)" \
                            " VALUES ( %s, %s, %s, %s) " \
                            "ON DUPLICATE KEY UPDATE `d03_1`=VALUES(`d03_1`), `d03_2`=VALUES(`d03_2`), " \
                            "`d03_3`=VALUES(`d03_3`);"
            row_count = cursor.executemany(sql_statement, grid_mappings_list)
        connection.commit()
        return row_count
    except Exception as ex:
        connection.rollback()
        error_message = "Insertion of flo2d grid mappings failed."
        logger.error(error_message)
        traceback.print_exc()
        return False
    finally:
        if connection is not None:
            connection.close()


def get_obs_to_d03_grid_mappings_for_rainfall(pool, grid_interpolation):

    """
    Retrieve obs to d03 grid mappings
    :param pool: database connection pool
    :param grid_interpolation: grid interpolation method
    :return: dictionary with grid ids as keys and corresponding obs1, obs2, obs3 station ids as a list
    """

    obs_grid_mappings = {}

    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            sql_statement = "SELECT `grid_id`,`d03_1`,`d03_2`,`d03_3` FROM `grid_map_obs` " \
                            "WHERE `grid_id` like %s ESCAPE '$'"
            row_count = cursor.execute(sql_statement, "rainfall$_%$_{}".format(grid_interpolation))
            if row_count > 0:
                results = cursor.fetchall()
                for dict in results:
                    obs_grid_mappings[dict.get("grid_id")] = [dict.get("d03_1"), dict.get("d03_2"), dict.get("d03_3")]
                return obs_grid_mappings
            else:
                return None
    except Exception as ex:
        error_message = "Retrieving flo2d to obs grid mappings failed"
        logger.error(error_message)
        traceback.print_exc()
        raise DatabaseAdapterError(error_message, ex)
    finally:
        if connection is not None:
            connection.close()
