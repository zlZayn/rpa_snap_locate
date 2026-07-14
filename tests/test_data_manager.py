import json
import os
import pytest

from data.data_manager import DataManager


@pytest.fixture
def dm(tmp_path):
    os.makedirs(tmp_path / "workflows", exist_ok=True)
    dm = DataManager.__new__(DataManager)
    dm._workflows_dir = str(tmp_path / "workflows")
    return dm


class TestSaveWorkflowTimeline:
    def test_save_and_load_back(self, dm):
        events = [
            {
                "index": 1,
                "type": "mouse_down",
                "button": "left",
                "offset_ns": 0,
                "method": "fixed",
                "norm_x": 0.5,
                "norm_y": 0.5,
                "window_title": "Notepad",
                "dpi_scale": 1.0,
            },
            {
                "index": 2,
                "type": "mouse_up",
                "button": "left",
                "offset_ns": 73400000,
                "position_from_event": 1,
            },
        ]
        path = dm.save_workflow_timeline(events, "20260711_150000_000000", "test")
        assert "test-" in path
        assert "-2events.json" in path

        loaded = dm.load_workflow(path)
        assert loaded["format"] == "timeline"
        assert loaded["timeline"]["clock"] == "monotonic"
        assert loaded["events"] == events

    def test_invalid_events_raises(self, dm):
        with pytest.raises(ValueError):
            dm.save_workflow_timeline(
                [{"index": 1, "type": "mouse_down", "button": "left", "offset_ns": 0}],
                "ts",
            )

    def test_unsupported_format_raises(self, dm):
        path = os.path.join(dm._workflows_dir, "bad.json")
        workflow = {"format": "unknown", "steps": []}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(workflow, f)

        with pytest.raises(ValueError, match="unsupported workflow format"):
            dm.load_workflow(path)
