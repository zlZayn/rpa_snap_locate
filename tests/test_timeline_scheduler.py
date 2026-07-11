from unittest.mock import Mock, patch

import pytest

from engine.timeline_scheduler import TimelineScheduler


class FakeClock:
    def __init__(self):
        self.now = 0

    def perf_counter_ns(self):
        self.now += 100
        return self.now

    def sleep(self, seconds):
        self.now += int(seconds * 1_000_000_000)


def _down(index, offset):
    return {
        "index": index,
        "type": "mouse_down",
        "button": "left",
        "offset_ns": offset,
    }


def _up(index, offset):
    return {
        "index": index,
        "type": "mouse_up",
        "button": "left",
        "offset_ns": offset,
    }


def test_preparation_delay_is_included_in_lateness_report():
    clock = FakeClock()
    prepare_calls = 0

    def prepare(_event):
        nonlocal prepare_calls
        prepare_calls += 1
        if prepare_calls == 2:
            clock.now += 15_000_000

    scheduler = TimelineScheduler(late_warning_ms=1)
    events = [
        _down(1, 0),
        _up(2, 10_000_000),
        _down(3, 20_000_000),
        _up(4, 30_000_000),
    ]

    with (
        patch(
            "engine.timeline_scheduler.time.perf_counter_ns",
            side_effect=clock.perf_counter_ns,
        ),
        patch("engine.timeline_scheduler.time.sleep", side_effect=clock.sleep),
    ):
        report = scheduler.run(events, prepare, Mock(), Mock())

    second_down = next(item for item in report["executions"] if item["index"] == 3)
    assert second_down["lateness_ns"] >= 5_000_000
    assert report["status"] == "degraded"


def test_interrupted_timeline_releases_pressed_button():
    clock = FakeClock()
    up = Mock()
    prepare_calls = 0

    def prepare(_event):
        nonlocal prepare_calls
        prepare_calls += 1
        if prepare_calls == 2:
            raise RuntimeError("prepare failed")

    with (
        patch(
            "engine.timeline_scheduler.time.perf_counter_ns",
            side_effect=clock.perf_counter_ns,
        ),
        patch("engine.timeline_scheduler.time.sleep", side_effect=clock.sleep),
        pytest.raises(RuntimeError, match="prepare failed"),
    ):
        TimelineScheduler().run(
            [_down(1, 0), _down(2, 10_000_000)],
            prepare,
            Mock(),
            up,
        )

    up.assert_called_once_with("left")
