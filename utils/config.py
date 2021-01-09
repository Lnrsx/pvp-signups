from utils.misc import get_logger
import json
import os
from socket import gethostname

logger = get_logger("PvpSignups")
devmode = gethostname() == 'DESKTOP-SKJPMQE'


class DataManager:
    def __init__(self, configpath, devmode_override=False):
        if devmode and not devmode_override:
            logger.info("Running on Developer Mode")
            self.configpath = "devconfig.json"
        else:
            self.configpath = configpath
        if os.path.isfile(self.configpath):
            try:
                self.settings = {**json.load(open(self.configpath, "r"))}
                self.validate()
            except json.decoder.JSONDecodeError:
                logger.error("Invalid syntax in the config file")
                exit()
        else:
            logger.error("No config file detected")
            exit()
        self.data = {**json.load(open("data/data.json", "r"))}
        self.pricing = {**json.load(open("data/sylvanas/pricing.json", "r"))}

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

    def spec_from_emote(self, spec_emote):
        for cls, specs in self.data["spec_emotes"].items():
            for spec, emote in specs.items():
                if emote == spec_emote:
                    return spec, cls

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


cfg = DataManager("data/sylvanas/config.json")
