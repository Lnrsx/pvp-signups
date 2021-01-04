from utils.misc import get_logger
import json
import os
from socket import gethostname

logger = get_logger("PvpSignups")
devmode = gethostname() == 'DESKTOP-SKJPMQE'


class DataManager:
    def __init__(self):
        #  Debug mode determines if the bot should validate it's own settings and files before startup.
        #  Once the bot is fully set up, this can be set to false to improve startup time
        self.debug = True
        if devmode:
            logger.info("Running on Developer Mode")
            self.configpath = "devconfig.json"
        else:
            self.configpath = "config.json"
        if self.debug:
            if os.path.isfile(self.configpath):
                try:
                    self.settings = {**json.load(open(self.configpath, "r"))}
                    self.validate()
                except json.decoder.JSONDecodeError:
                    logger.error("Invalid syntax in the config file")
                    exit()
            else:
                if os.path.isfile("config.json.example"):
                    logger.error("Remove the .example from config.json.example and fill in the relevant fields")
                else:
                    logger.error("No config file detected")
                exit()
        else:
            self.settings = {**json.load(open(self.configpath, "r"))}
        self.data = {**json.load(open("data/data.json", "r"))}
        self.pricing = {**json.load(open("data/pricing.json", "r"))}

    def cfgset(self, key, value):
        if key in self.settings.keys():
            self.settings[key] = value
            with open(self.configpath, "w") as f:
                json.dump(self.settings, f, indent=4)
            return True

        else:
            logger.error(f"No settings named {key}")
            return False

    def cfgupdate(self, key):
        if key in self.settings.keys():
            with open(self.configpath, "w") as f:
                json.dump(self.settings, f, indent=4)
            return True
        else:
            logger.error(f"No settings named {key}")
            return False

    def validate(self):
        try:
            assert self.settings["discord_token"] != "YOUR_DISCORD_TOKEN", "a discord token"
            if self.settings["auto_faction_class_input"]:
                assert self.settings["wowapi_id"] != "YOUR_WOWAPI_ID", "a wowapi ID"
                assert self.settings["wowapi_secret"] != "YOUR_WOWAPI_SECRET", "a wowapi secret"
            assert self.settings["guild_id"] != 0, "a guild ID"
            return True
        except AssertionError as e:
            logger.error(f"Setting in config file invalid: you must provide {e}")
            exit()


cfg = DataManager()
