# app/config/config_manager.py
"""Configuration manager for Aditus.

Provides safe reading/writing of ``aditus_config.json`` with automatic
fallback to defaults when the file is missing or corrupted.

The manager is thread‑safe and logs all operations via :class:`app.utils.logger.Logger`.
"""

import json
import os
import threading
import sys
import copy
import time
from typing import Any, Dict, List
def resource_path(relative_path: str) -> str:
    """Return absolute path to a resource, works for dev and PyInstaller.
    Uses sys._MEIPASS when frozen, otherwise the directory of this file.
    """
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)
from app.utils.logger import Logger

DEFAULT_CONFIG = {
    "trigger": {
        "type": "clap",  # or "hotkey"
        "hotkey": "ctrl+shift+j"
    },
    "clap": {
        "threshold": 15.0,
        "interval": 0.4,
        "cooldown": 5.0,
        "debounce": 0.08
    },
    "permissions": {
        "mic_enabled": True,
        "startup_enabled": True
    },
    "apps": []  # List of dicts: {"name": "Notepad", "path": "C:\\Windows\\system32\\notepad.exe"}
}


class ConfigManager:
    """Singleton‑style config accessor.

    The class is deliberately lightweight – an instance is created where
    needed and internally guards all file I/O with a ``threading.Lock``.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config_path: str = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init(config_path)
        return cls._instance

    def _init(self, config_path: str = None):
        self.logger = Logger()
        self._file_lock = threading.RLock()
        if config_path:
            self.config_path = config_path
        else:
            # Use resource_path to locate the config file in both dev and frozen mode
            self.config_path = resource_path("aditus_config.json")
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        with self._file_lock:
            if not os.path.isfile(self.config_path):
                self.logger.info(f"Config not found – creating default at {self.config_path}")
                self._data = copy.deepcopy(DEFAULT_CONFIG)
                self._write()
                return
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                self.logger.info(f"Config loaded from {self.config_path}")
            except Exception as e:
                self.logger.error(f"Failed to read config – using defaults. Error: {e}")
                # Backup corrupted config
                backup_path = self.config_path + ".backup.json"
                try:
                    os.replace(self.config_path, backup_path)
                    self.logger.warning(f"Corrupted config backed up to {backup_path}")
                except Exception as be:
                    self.logger.error(f"Failed to backup corrupted config: {be}")
                self._data = copy.deepcopy(DEFAULT_CONFIG)
                self._write()

    def _write(self) -> None:
        start = time.perf_counter()
        with self._file_lock:
            tmp_path = f"{self.config_path}.tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)
                os.replace(tmp_path, self.config_path)
                self.logger.info(f"Config persisted to {self.config_path}")
            except Exception as e:
                self.logger.error(f"Failed to write config file: {e}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        self.logger.debug(f"Config write duration: {time.perf_counter() - start:.4f}s")

    def get(self, key_path: List[str]) -> Any:
        node = self._data
        for key in key_path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
            if node is None:
                break
        return node

    def set(self, key_path: List[str], value: Any) -> None:
        node = self._data
        for key in key_path[:-1]:
            node = node.setdefault(key, {})
        node[key_path[-1]] = value
        self.logger.info(f"Config updated: {'.'.join(key_path)} = {value}")
        self._write()

    # Convenience helpers -------------------------------------------------
    def get_trigger_type(self) -> str:
        return self.get(["trigger", "type"]) or "clap"

    def set_trigger_type(self, trigger_type: str) -> None:
        self.set(["trigger", "type"], trigger_type)

    def get_apps(self) -> List[Dict[str, str]]:
        return self.get(["apps"]) or []

    def add_app(self, name: str, path: str) -> None:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Executable not found: {path}")
        apps = self.get_apps()
        if any(app["path"].lower() == path.lower() for app in apps):
            raise ValueError("Application already added.")
        apps.append({"name": name, "path": path})
        self.set(["apps"], apps)

    def remove_app(self, path: str) -> None:
        apps = self.get_apps()
        filtered = [app for app in apps if app["path"].lower() != path.lower()]
        if len(filtered) == len(apps):
            raise ValueError("Application not found.")
        self.set(["apps"], filtered)
