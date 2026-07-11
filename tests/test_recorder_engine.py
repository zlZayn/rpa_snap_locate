import unittest
from unittest.mock import Mock, call

from engine.recorder_engine import RecorderEngine, RecorderState


class RecorderEngineSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RecorderEngine.__new__(RecorderEngine)
        self.engine._steps = []
        self.engine._step_builder = Mock()
        self.engine._data_manager = Mock()
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


if __name__ == "__main__":
    unittest.main()
