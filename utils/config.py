from utils.misc import get_logger
import json
import os
from socket import gethostname

logger = get_logger("PvpSignups")

devmode_override = True
devmode = not devmode_override or gethostname() == 'DESKTOP-SKJPMQE'


def load_attrs(obj, path):
    if os.path.isfile(path):
        try:
            for k, v in {**json.load(open(path, "r"))}.items():
                setattr(obj, k, v)
        except json.decoder.JSONDecodeError:
            logger.error("Invalid syntax in the shared config file")
            exit()
    else:
        logger.error(f"Missing config file at path: {path}")
        exit()


class ConfigManager(object):
    def __init__(self, directory, subdir):
        self.directory = directory
        self.subdir = subdir
        load_attrs(self, self.directory+self.subdir)

    def set(self, key, value):
        if key in self.__dict__.keys():
            setattr(self, key, value)
            file = json.load(open(self.directory+self.subdir, "r"))
            file[key] = value
            json.dump(file, open(self.directory+self.subdir, "w"), indent=4)
            return True

        else:
            logger.error(f"No settings named {key}")
            return False

    def update(self):
        json.dump(self.__dict__, open(self.directory+self.subdir, "w"), indent=4)


class GenDataManager(object):
    def __init__(self):
        self.datapath = "data/data.json"
        load_attrs(self, self.datapath)

    def spec_from_emote(self, spec_emote):
        for cls, specs in getattr(self, "spec_emotes").items():
            for spec, emote in specs.items():
                if emote == spec_emote:
                    return spec, cls


cfg = ConfigManager("data", "/config.json")
data = GenDataManager()

icfg, ipricing = {}, {}
if not devmode:
    if devmode_override:
        logger.info("Developer mode override enabled")
    instances = os.listdir('./data/instances')
    if not instances:
        logger.error("No instances detected")
        exit()
    for filename in instances:
        icfg[filename] = ConfigManager('data/instances/'+filename, "/config.json")
        ipricing[filename] = ConfigManager('data/instances/'+filename, "/pricing.json")
else:
    logger.info("! Running on developer mode !")
    icfg["pvp_bookings"] = ConfigManager('data/pvp_bookings', "/config.json")
    ipricing["pvp_bookings"] = ConfigManager('data/pvp_bookings', "/pricing.json")
