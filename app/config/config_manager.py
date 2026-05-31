import json
import logging
import os

logger = logging.getLogger("aditus.config")


class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.data = {}
        self.load()

    def load(self) -> dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self.data

    def save(self, data: dict = None):
        if data is not None:
            self.data.update(data)
        try:
            parent = os.path.dirname(self.config_path)
            os.makedirs(parent, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            logger.exception("Failed to save config to %s", self.config_path)

    def get(self, key: str, default=None):
        return self.data.get(key, default)
