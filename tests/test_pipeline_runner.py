import json

import pytest

from engine.pipeline_runner import PipelineRunner
from engine.workflow_validator import ValidationError
from core.locator_protocol import create_locator


def _write_workflow(tmp_path, workflow):
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(workflow), encoding="utf-8")
    return str(path)


def test_unknown_workflow_format_is_rejected(tmp_path):
    path = _write_workflow(tmp_path, {"format": "unknown", "events": []})
    runner = PipelineRunner.__new__(PipelineRunner)

    with pytest.raises(ValueError, match="unsupported workflow format"):
        runner.run(path)


def test_llm_locator_is_not_advertised_as_a_supported_method():
    with pytest.raises(ValueError, match="unknown locator method: llm"):
        create_locator("llm")


def test_timeline_is_validated_before_replay_setup(tmp_path):
    path = _write_workflow(
        tmp_path,
        {
            "format": "timeline",
            "events": [
                {
                    "index": 1,
                    "type": "mouse_down",
                    "button": "left",
                    "offset_ns": 0,
                }
            ],
        },
    )
    runner = PipelineRunner.__new__(PipelineRunner)
    runner._start_delay = 0

    with pytest.raises(ValidationError, match="method"):
        runner.run(path)
