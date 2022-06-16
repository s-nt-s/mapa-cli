from munch import Munch
from os.path import join, isfile, dirname, realpath
from os import getcwd
import yaml

__location__ = realpath(
    join(getcwd(), dirname(__file__))
)
__location__ = join(__location__, "..")
print(__location__)

def get_config(fl="config.yml"):
    fl = join(__location__, fl)
    if not isfile(fl):
        raise Exception("No existe: "+str(fl))
    with open(fl, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    config = Munch.fromDict(config)
    return config

CNF=get_config()