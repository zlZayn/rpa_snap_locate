import json
import os
from datetime import datetime
from config.config_manager import ConfigManager


class DataManager:
    def __init__(self):
        self._config = ConfigManager()
        if not self._config._data:
            self._config.load()
        self._workflows_dir = self._config.get("paths", "workflows_dir")
        os.makedirs(self._workflows_dir, exist_ok=True)

    def new_recording(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_workflow(self, steps: list, session_name: str) -> str:
        dir_name = f"{session_name}-{len(steps)}steps"
        path = os.path.join(self._workflows_dir, f"{dir_name}.json")
        workflow = {
            "version": "4.0",
            "created_at": datetime.now().isoformat(),
            "steps": steps,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        return path