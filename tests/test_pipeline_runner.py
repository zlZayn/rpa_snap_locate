import json

import pytest

from engine.pipeline_runner import PipelineRunner
from engine.workflow_validator import ValidationError


def _write_workflow(tmp_path, workflow):
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(workflow), encoding="utf-8")
    return str(path)


def test_unknown_workflow_version_is_rejected(tmp_path):
    path = _write_workflow(tmp_path, {"version": "99.0", "events": []})
    runner = PipelineRunner.__new__(PipelineRunner)

    with pytest.raises(ValueError, match="unsupported workflow version"):
        runner.run(path)


def test_v5_is_validated_before_replay_setup(tmp_path):
    path = _write_workflow(
        tmp_path,
        {
            "version": "5.0",
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
