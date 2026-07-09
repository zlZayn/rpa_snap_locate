import yaml
import os
from typing import Any


class ConfigManager:
    _instance = None
    _data: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = None) -> dict:
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "system.yaml"
            )
        with open(config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)
        return self._data

    def get(self, *keys: str, default: Any = None) -> Any:
        value = self._data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def reload(self) -> dict:
        self._data = {}
        return self.load()