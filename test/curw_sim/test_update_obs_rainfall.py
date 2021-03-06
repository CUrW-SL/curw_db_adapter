import traceback
from datetime import datetime, timedelta

from db_adapter.curw_sim.constants import HecHMS
from db_adapter.curw_sim.grids import GridInterpolationEnum
from db_adapter.curw_sim.timeseries import MethodEnum
from db_adapter.curw_sim.rainfall import update_rainfall_fcsts


if __name__=="__main__":
    try:
        method = MethodEnum.getAbbreviation(MethodEnum.MME)
        grid_interpolation = GridInterpolationEnum.getAbbreviation(GridInterpolationEnum.MDPA)

        # print("{} : ####### Insert obs rainfall for FLO2D 250 grids".format(datetime.now()))
        update_rainfall_fcsts(target_model=HecHMS, method=method, grid_interpolation=grid_interpolation, model="WRF_C", version="v4")

    except Exception as e:
        traceback.print_exc()
    finally:
        print("{} : ####### fcst rainfall insertion process finished for {} #######".format(datetime.now(), HecHMS))
