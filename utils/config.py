from utils.misc import get_logger
import json
import os
from socket import gethostname

logger = get_logger("PvpSignups")
devmode = gethostname() == 'DESKTOP-SKJPMQE'


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
    def __init__(self, configpath):
        self.configpath = configpath
        load_attrs(self, self.configpath)

    def set(self, key, value):
        if key in self.__dict__.keys():
            setattr(self, key, value)
            file = json.load(open(self.configpath, "r"))
            file[key] = value
            json.dump(open(self.configpath, "w"), file, indent=4)
            return True

        else:
            logger.error(f"No settings named {key}")
            return False

    def update(self):
        json.dump(self.__dict__, open(self.configpath, "w"), indent=4)


class GenDataManager(object):
    def __init__(self):
        self.datapath = "data/data.json"
        load_attrs(self, self.datapath)

    def spec_from_emote(self, spec_emote):
        for cls, specs in getattr(self, "spec_emotes").items():
            for spec, emote in specs.items():
                if emote == spec_emote:
                    return spec, cls


cfg = ConfigManager("data/config.json")
data = GenDataManager()

icfg = {}
if not devmode:
    for filename in os.listdir('./data/instances'):
        icfg[filename] = ConfigManager('data/instances'+filename+"config.json")
else:
    icfg["developer"] = ConfigManager('data/developer/config.json')
