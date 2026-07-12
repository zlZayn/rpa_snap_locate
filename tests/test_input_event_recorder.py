from unittest.mock import Mock, patch

import mouse

from engine.input_event_recorder import InputEventRecorder
from engine.workflow_validator import validate_v5_events


def _make_recorder():
    perception = Mock()
    perception.get_mouse_position.return_value = (300, 400)
    perception.get_active_window.return_value = {"title": "Test"}
    perception.get_dpi_scale.return_value = 1.0
    perception.get_logical_resolution.return_value = (1000, 1000)
    with patch(
        "engine.input_event_recorder.PerceptionProvider", return_value=perception
    ):
        recorder = InputEventRecorder()
    return recorder, perception


def _record(recorder, events, timestamps):
    with (
        patch("engine.input_event_recorder.mouse.hook", return_value="hook"),
        patch("engine.input_event_recorder.mouse.unhook"),
        patch(
            "engine.input_event_recorder.time.perf_counter_ns",
            side_effect=timestamps,
        ),
    ):
        recorder.start_recording()
        for event in events:
            recorder._on_mouse_event(event)
        return recorder.stop_recording()


def test_first_event_keeps_wait_since_f2_and_uses_cursor_position_at_start():
    recorder, _ = _make_recorder()
    events = _record(
        recorder,
        [
            mouse.ButtonEvent("down", "left", 0),
            mouse.ButtonEvent("up", "left", 0),
        ],
        [500, 1_000, 1_075],
    )

    assert events[0]["offset_ns"] == 500
    assert events[0]["norm_x"] == 0.3
    assert events[0]["norm_y"] == 0.4
    assert events[1]["offset_ns"] == 575
    validate_v5_events(events)


def test_interleaved_buttons_pair_with_their_own_down_event():
    recorder, _ = _make_recorder()
    events = _record(
        recorder,
        [
            mouse.ButtonEvent("down", "left", 0),
            mouse.ButtonEvent("down", "right", 0),
            mouse.ButtonEvent("up", "left", 0),
            mouse.ButtonEvent("up", "right", 0),
        ],
        [50, 100, 110, 120, 130],
    )

    assert events[2]["position_from_event"] == 1
    assert events[3]["position_from_event"] == 2
    validate_v5_events(events)


def test_windows_double_event_is_preserved_as_second_down():
    recorder, _ = _make_recorder()
    events = _record(
        recorder,
        [
            mouse.ButtonEvent("down", "left", 0),
            mouse.ButtonEvent("up", "left", 0),
            mouse.ButtonEvent("double", "left", 0),
            mouse.ButtonEvent("up", "left", 0),
        ],
        [50, 100, 150, 220, 270],
    )

    assert [event["type"] for event in events] == [
        "mouse_down",
        "mouse_up",
        "mouse_down",
        "mouse_up",
    ]
    assert events[1]["position_from_event"] == 1
    assert events[3]["position_from_event"] == 3
    validate_v5_events(events)


