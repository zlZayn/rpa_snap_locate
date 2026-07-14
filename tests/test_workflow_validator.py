import pytest
from engine.workflow_validator import validate_timeline_events, ValidationError


def _make_down(index=1, offset_ns=0, **kwargs) -> dict:
    event = {
        "index": index,
        "type": "mouse_down",
        "button": "left",
        "offset_ns": offset_ns,
        "method": "fixed",
        "norm_x": 0.5,
        "norm_y": 0.5,
        "window_title": "Test",
        "dpi_scale": 1.0,
    }
    event.update(kwargs)
    return event


def _make_up(index=2, offset_ns=73400000, position_from_event=1, **kwargs) -> dict:
    event = {
        "index": index,
        "type": "mouse_up",
        "button": "left",
        "offset_ns": offset_ns,
        "position_from_event": position_from_event,
    }
    event.update(kwargs)
    return event


class TestValidateTimelineEvents:
    def test_valid_single_click(self):
        events = [
            _make_down(index=1, offset_ns=0),
            _make_up(index=2, offset_ns=73400000, position_from_event=1),
        ]
        validate_timeline_events(events)

    def test_valid_double_click(self):
        events = [
            _make_down(index=1, offset_ns=0),
            _make_up(index=2, offset_ns=73400000, position_from_event=1),
            _make_down(index=3, offset_ns=151600000),
            _make_up(index=4, offset_ns=226100000, position_from_event=3),
        ]
        validate_timeline_events(events)

    def test_empty_events_raises(self):
        with pytest.raises(ValidationError):
            validate_timeline_events([])

    def test_missing_down_pair_raises(self):
        events = [
            _make_down(index=1, offset_ns=0),
        ]
        with pytest.raises(ValidationError, match="without matching mouse_up"):
            validate_timeline_events(events)

    def test_orphan_up_raises(self):
        events = [
            _make_up(index=2, offset_ns=73400000, position_from_event=99),
        ]
        with pytest.raises(ValidationError, match="non-existent mouse_down"):
            validate_timeline_events(events)

    def test_duplicate_index_raises(self):
        events = [
            _make_down(index=1, offset_ns=0),
            _make_up(index=1, offset_ns=73400000, position_from_event=1),
        ]
        with pytest.raises(ValidationError, match="duplicate event index"):
            validate_timeline_events(events)

    def test_unsorted_offset_raises(self):
        events = [
            _make_down(index=1, offset_ns=100),
            _make_up(index=2, offset_ns=50, position_from_event=1),
        ]
        with pytest.raises(ValidationError, match="not sorted"):
            validate_timeline_events(events)

    def test_negative_offset_raises(self):
        events = [
            _make_down(index=1, offset_ns=-1),
        ]
        with pytest.raises(ValidationError):
            validate_timeline_events(events)

    def test_up_with_position_info_raises(self):
        events = [
            _make_down(index=1, offset_ns=0),
            {
                "index": 2,
                "type": "mouse_up",
                "button": "left",
                "offset_ns": 73400000,
                "position_from_event": 1,
                "norm_x": 0.5,
            },
        ]
        with pytest.raises(ValidationError, match="norm_x"):
            validate_timeline_events(events)

    def test_down_with_position_from_event_raises(self):
        events = [
            {
                "index": 1,
                "type": "mouse_down",
                "button": "left",
                "offset_ns": 0,
                "position_from_event": 2,
                "method": "fixed",
                "norm_x": 0.5,
                "norm_y": 0.5,
                "window_title": "Test",
                "dpi_scale": 1.0,
            },
        ]
        with pytest.raises(ValidationError, match="position_from_event"):
            validate_timeline_events(events)

    def test_missing_method_on_down_raises(self):
        events = [
            {"index": 1, "type": "mouse_down", "button": "left", "offset_ns": 0},
        ]
        with pytest.raises(ValidationError, match="method"):
            validate_timeline_events(events)

    def test_missing_position_from_event_on_up_raises(self):
        events = [
            _make_down(index=1, offset_ns=0),
            {"index": 2, "type": "mouse_up", "button": "left", "offset_ns": 73400000},
        ]
        with pytest.raises(ValidationError, match="position_from_event"):
            validate_timeline_events(events)

    def test_invalid_type_raises(self):
        events = [
            {"index": 1, "type": "hover", "button": "left", "offset_ns": 0},
        ]
        with pytest.raises(ValidationError, match="invalid type"):
            validate_timeline_events(events)

    def test_wrong_button_raises(self):
        events = [
            _make_down(index=1, offset_ns=0, button="extra"),
        ]
        with pytest.raises(ValidationError, match="invalid button"):
            validate_timeline_events(events)

    def test_up_button_must_match_down(self):
        events = [
            _make_down(index=1, offset_ns=0, button="left"),
            _make_up(
                index=2,
                offset_ns=10,
                position_from_event=1,
                button="right",
            ),
        ]
        with pytest.raises(ValidationError, match="does not match"):
            validate_timeline_events(events)

    def test_down_cannot_have_two_ups(self):
        events = [
            _make_down(index=1, offset_ns=0),
            _make_up(index=2, offset_ns=10, position_from_event=1),
            _make_up(index=3, offset_ns=20, position_from_event=1),
        ]
        with pytest.raises(ValidationError):
            validate_timeline_events(events)

    def test_same_button_cannot_be_pressed_twice_without_release(self):
        events = [
            _make_down(index=1, offset_ns=0),
            _make_down(index=2, offset_ns=10),
        ]
        with pytest.raises(ValidationError, match="pressed again"):
            validate_timeline_events(events)

    def test_first_event_may_include_wait_since_recording_started(self):
        events = [
            _make_down(index=1, offset_ns=100),
            _make_up(index=2, offset_ns=200, position_from_event=1),
        ]
        validate_timeline_events(events)
