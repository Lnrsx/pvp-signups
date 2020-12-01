from utils.misc import get_logger
import json
import os

logger = get_logger("PvpSignups")


class ConfigManager:
    # TODO add handling for all data files
    # TODO fix class_emotes occourances
    def __init__(self):
        if os.path.isfile("config.json"):
            self.settings = {**json.load(open("config.json", "r"))}
        else:
            logger.error("No config file detected")
            exit()
        self.data = {**json.load(open("data/data.json", "r"))}
        self.pricing = {**json.load(open("data/pricing.json", "r"))}

    def cfgset(self, key, value):
        if key in self.settings.keys():
            self.settings[key] = value
            with open("config.json", "w") as f:
                json.dump(self.settings, f)

        else:
            logger.error(f"No settings named {key}")


cfg = ConfigManager()
