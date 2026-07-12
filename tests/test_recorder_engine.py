import unittest
from unittest.mock import Mock, call

from engine.recorder_engine import RecorderEngine, RecorderState


class LegacyRecorderEngineSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RecorderEngine.__new__(RecorderEngine)
        self.engine._mode = "legacy"
        self.engine._steps = []
        self.engine._events = []
        self.engine._step_builder = Mock()
        self.engine._data_manager = Mock()
        self.engine._input_recorder = Mock()
        self.engine._perception = Mock()
        self.engine._cancel_event = Mock()
        self.engine._ts = "ts-1"
        self.engine.state = RecorderState.IDLE
        self.engine._box_point1 = None
        self.engine._box_point2 = None
        self.engine._box_region = None
        self.engine._prompt_name = Mock(return_value="")

    def test_empty_save_is_a_no_op(self) -> None:
        message = self.engine.save()

        self.assertEqual(message, "no steps to save")
        self.engine._data_manager.save_workflow.assert_not_called()
        self.engine._data_manager.new_ts.assert_not_called()
        self.engine._step_builder.reset_counter.assert_not_called()

    def test_save_writes_current_steps_then_resets_everything(self) -> None:
        steps = [{"index": 1}, {"index": 2}]
        self.engine._steps.extend(steps)
        self.engine.state = RecorderState.WAITING_TARGET
        self.engine._box_point1 = (10, 20)
        self.engine._box_point2 = (30, 40)
        self.engine._box_region = {"left": 10, "top": 20, "width": 20, "height": 20}
        self.engine._data_manager.save_workflow.return_value = "workflow-1.json"
        self.engine._data_manager.new_ts.return_value = "ts-2"

        message = self.engine.save()

        self.engine._data_manager.save_workflow.assert_called_once_with(
            steps, "ts-1", ""
        )
        self.assertEqual(self.engine._steps, [])
        self.engine._step_builder.reset_counter.assert_called_once_with()
        self.assertEqual(self.engine._ts, "ts-2")
        self.assertEqual(self.engine.state, RecorderState.IDLE)
        self.assertIsNone(self.engine._box_point1)
        self.assertIsNone(self.engine._box_point2)
        self.assertIsNone(self.engine._box_region)
        self.assertEqual(
            message,
            "saved 2 steps to workflow-1.json. "
            "Recording reset, ready for new workflow.",
        )

    def test_consecutive_saves_only_write_new_steps(self) -> None:
        self.engine._data_manager.save_workflow.side_effect = [
            "workflow-1.json",
            "workflow-2.json",
        ]
        self.engine._data_manager.new_ts.side_effect = [
            "ts-2",
            "ts-3",
        ]

        first_steps = [{"index": 1}, {"index": 2}]
        self.engine._steps.extend(first_steps)
        self.engine.save()

        second_steps = [{"index": 1}, {"index": 2}, {"index": 3}]
        self.engine._steps.extend(second_steps)
        self.engine.save()

        self.assertEqual(
            self.engine._data_manager.save_workflow.call_args_list,
            [
                call(first_steps, "ts-1", ""),
                call(second_steps, "ts-2", ""),
            ],
        )
        self.assertEqual(self.engine._step_builder.reset_counter.call_count, 2)

    def test_clear_resets_state_without_changing_ts(self) -> None:
        self.engine._steps.append({"index": 1})
        self.engine.state = RecorderState.WAITING_SECOND
        self.engine._box_point1 = (10, 20)

        message = self.engine.clear()

        self.assertEqual(message, "workflow cleared")
        self.assertEqual(self.engine._ts, "ts-1")
        self.engine._data_manager.new_ts.assert_not_called()
        self.assertEqual(self.engine.state, RecorderState.IDLE)
        self.assertEqual(self.engine._steps, [])


class TimelineRecorderEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RecorderEngine.__new__(RecorderEngine)
        self.engine._mode = "timeline"
        self.engine._steps = []
        self.engine._events = []
        self.engine._step_builder = Mock()
        self.engine._data_manager = Mock()
        self.engine._input_recorder = Mock()
        self.engine._perception = Mock()
        self.engine._cancel_event = Mock()
        self.engine._ts = "ts-1"
        self.engine.state = RecorderState.IDLE
        self.engine._box_point1 = None
        self.engine._box_point2 = None
        self.engine._box_region = None
        self.engine._prompt_name = Mock(return_value="")

    def test_f2_starts_and_stops_recording(self) -> None:
        self.engine._input_recorder.stop_recording.return_value = []
        msg1 = self.engine.on_f2()
        self.assertEqual(msg1, "recording started")
        self.engine._input_recorder.start_recording.assert_called_once()
        self.assertEqual(self.engine.state, RecorderState.RECORDING)

        msg2 = self.engine.on_f2()
        self.assertEqual(msg2, "recording stopped")
        self.engine._input_recorder.stop_recording.assert_called_once()
        self.assertEqual(self.engine.state, RecorderState.IDLE)

    def test_f3_box_selection_injects_screenshot_event(self) -> None:
        self.engine.state = RecorderState.RECORDING
        self.engine._perception.get_mouse_position.side_effect = [
            (100, 200),
            (300, 400),
        ]

        self.engine.on_f3()
        self.assertEqual(self.engine.state, RecorderState.RECORDING_WAITING_SECOND)

        self.engine.on_f3()
        self.assertEqual(self.engine.state, RecorderState.RECORDING)
        self.engine._input_recorder.capture_screenshot.assert_called_once_with(
            {"left": 100, "top": 200, "width": 200, "height": 200},
        )

    def test_cancel_box_selection_during_recording(self) -> None:
        self.engine.state = RecorderState.RECORDING_WAITING_SECOND
        self.engine._box_point1 = (100, 200)

        msg = self.engine.on_cancel()
        self.assertEqual(msg, "box selection cancelled")
        self.assertEqual(self.engine.state, RecorderState.RECORDING)

    def test_empty_save_in_timeline_mode(self) -> None:
        message = self.engine.save()
        self.assertEqual(message, "no events to save")
        self.engine._data_manager.save_workflow_v5.assert_not_called()

    def test_save_with_events_calls_v5(self) -> None:
        events = [{"index": 1, "type": "mouse_down"}]
        self.engine._events.extend(events)
        self.engine._data_manager.save_workflow_v5.return_value = "v5-workflow.json"
        self.engine._data_manager.new_ts.return_value = "ts-2"

        message = self.engine.save()
        self.engine._data_manager.save_workflow_v5.assert_called_once_with(
            events,
            "ts-1",
            "",
        )
        self.assertEqual(self.engine._events, [])
        self.assertIn("saved 1 events", message)

    def test_save_stops_recording_first(self) -> None:
        self.engine.state = RecorderState.RECORDING
        self.engine._input_recorder.stop_recording.return_value = [
            {
                "index": 1,
                "type": "mouse_down",
                "button": "left",
                "offset_ns": 0,
                "method": "fixed",
                "norm_x": 0.5,
                "norm_y": 0.5,
                "window_title": "Test",
            },
            {
                "index": 2,
                "type": "mouse_up",
                "button": "left",
                "offset_ns": 50,
                "position_from_event": 1,
            },
        ]
        self.engine._data_manager.save_workflow_v5.return_value = "v5-workflow.json"

        self.engine.save()
        self.engine._input_recorder.stop_recording.assert_called_once()
        self.assertEqual(self.engine.state, RecorderState.IDLE)

    def test_f2_stop_preserves_events_for_later_save(self) -> None:
        events = [
            {
                "index": 1,
                "type": "mouse_down",
                "button": "left",
                "offset_ns": 0,
            },
            {
                "index": 2,
                "type": "mouse_up",
                "button": "left",
                "offset_ns": 50,
                "position_from_event": 1,
            },
        ]
        self.engine.state = RecorderState.RECORDING
        self.engine._input_recorder.stop_recording.return_value = events

        self.engine.on_f2()

        self.assertEqual(self.engine._events, events)

    def test_appending_segment_keeps_its_initial_wait_but_not_pause_time(self) -> None:
        self.engine._events = [
            {"index": 1, "type": "mouse_down", "offset_ns": 100},
            {
                "index": 2,
                "type": "mouse_up",
                "offset_ns": 150,
                "position_from_event": 1,
            },
        ]
        next_segment = [
            {"index": 1, "type": "mouse_down", "offset_ns": 30},
            {
                "index": 2,
                "type": "mouse_up",
                "offset_ns": 80,
                "position_from_event": 1,
            },
        ]

        self.engine._append_timeline_events(next_segment)

        self.assertEqual(
            [event["offset_ns"] for event in self.engine._events],
            [100, 150, 180, 230],
        )
        self.assertEqual(self.engine._events[3]["position_from_event"], 3)

    def test_clear_cancels_recording(self) -> None:
        self.engine.state = RecorderState.RECORDING
        message = self.engine.clear()
        self.assertEqual(message, "workflow cleared")
        self.engine._input_recorder.cancel_recording.assert_called_once()
        self.assertEqual(self.engine.state, RecorderState.IDLE)

    def test_save_validation_failure_reported(self) -> None:
        self.engine._events = [{"invalid": True}]
        self.engine._data_manager.save_workflow_v5.side_effect = ValueError(
            "missing required field 'index'"
        )
        message = self.engine.save()
        self.assertIn("save failed", message)
        self.assertEqual(self.engine._events, [{"invalid": True}])


if __name__ == "__main__":
    unittest.main()
