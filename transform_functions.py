from configobj import ConfigObj
from functions import get_config

config = ConfigObj('config.cfg')
config_reads = 0


def convert_to_mks(x, y=None):
    ppm = get_config("running","PPM")
    if not y is None:
        return x / ppm, y / ppm
    else:
        return x / ppm


def convert_from_mks(x, y=None):
    ppm = get_config("running", "PPM")
    if not y is None:
        return x * ppm, y * ppm
    else:
        return x * ppm