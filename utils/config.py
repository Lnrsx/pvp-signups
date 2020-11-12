from dotenv import load_dotenv
from utils.utils import get_logger
import json

logger = get_logger("PvpSignups")


class ConfigManager:

    def __init__(self):
        self.settings = {**json.load(open("config.json", "r"))}

    def set(self, key, value):
        if key in self.settings.keys():
            self.settings[key] = value
            with open("config.json", "w") as f:
                json.dump(self.settings, f)

        else:
            logger.error(f"No settings named {key}")
