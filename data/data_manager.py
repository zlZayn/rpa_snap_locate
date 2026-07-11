import json
import os
from datetime import datetime, timezone
from engine.workflow_validator import validate_v5_events
from config.config_manager import ConfigManager


class DataManager:
    def __init__(self):
        self._config = ConfigManager()
        if not self._config._data:
            self._config.load()
        self._workflows_dir = self._config.get("paths", "workflows_dir")
        os.makedirs(self._workflows_dir, exist_ok=True)

    def new_ts(self) -> str:
        # Microseconds prevent rapid consecutive saves with the same step count
        # from resolving to the same path and overwriting the earlier workflow.
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def save_workflow(self, steps: list, ts: str, name: str = "") -> str:
        if name:
            dir_name = f"{name}-{ts}-{len(steps)}steps"
        else:
            dir_name = f"{ts}-{len(steps)}steps"
        path = os.path.join(self._workflows_dir, f"{dir_name}.json")
        workflow = {
            "version": "4.0",
            "created_at": datetime.now().isoformat(),
            "steps": steps,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        return path

    def save_workflow_v5(
        self,
        events: list[dict],
        ts: str,
        name: str = "",
    ) -> str:
        validate_v5_events(events)

        if name:
            dir_name = f"{name}-{ts}-{len(events)}events"
        else:
            dir_name = f"{ts}-{len(events)}events"
        path = os.path.join(self._workflows_dir, f"{dir_name}.json")
        workflow: dict = {
            "version": "5.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timeline": {
                "clock": "monotonic",
                "unit": "ns",
                "zero": "first_input_event",
            },
            "events": events,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        return path

    def load_workflow(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
        version = workflow.get("version", "4.0")
        if version not in ("4.0", "5.0"):
            raise ValueError(f"unsupported workflow version: {version}")
        return workflow
