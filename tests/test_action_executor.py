import ctypes
import unittest
from unittest.mock import Mock, patch

from core.action_executor import (
    ActionExecutor,
    INPUT,
    MOUSEEVENTF_MIDDLEDOWN,
    MOUSEEVENTF_RIGHTDOWN,
)


class ActionExecutorSendInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = ActionExecutor.__new__(ActionExecutor)
        self.executor._user32 = Mock()
        self.executor._kernel32 = Mock()

    def test_send_mouse_button_accepts_one_inserted_event(self) -> None:
        self.executor._user32.SendInput.return_value = 1

        self.executor._send_mouse_button(0x0002)

        args = self.executor._user32.SendInput.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[2], ctypes.sizeof(INPUT))

    @patch("core.action_executor.ctypes.get_last_error", return_value=0)
    def test_send_mouse_button_explains_uipi_rejection(self, _get_error) -> None:
        self.executor._user32.SendInput.return_value = 0

        with self.assertRaisesRegex(PermissionError, "UIPI"):
            self.executor._send_mouse_button(0x0002)

    def test_mouse_down_sends_left_down(self) -> None:
        self.executor._user32.SendInput.return_value = 1
        self.executor.mouse_down("left")
        args = self.executor._user32.SendInput.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[2], ctypes.sizeof(INPUT))

    def test_mouse_up_sends_left_up(self) -> None:
        self.executor._user32.SendInput.return_value = 1
        self.executor.mouse_up("left")
        args = self.executor._user32.SendInput.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[2], ctypes.sizeof(INPUT))

    def test_right_and_middle_buttons_do_not_fall_back_to_left(self) -> None:
        with patch.object(self.executor, "_send_mouse_button") as send:
            self.executor.mouse_down("right")
            send.assert_called_once_with(MOUSEEVENTF_RIGHTDOWN)
            send.reset_mock()
            self.executor.mouse_down("middle")
            send.assert_called_once_with(MOUSEEVENTF_MIDDLEDOWN)

    def test_unknown_button_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported mouse button"):
            self.executor.mouse_down("x1")

    def test_prepare_target_skips_same_window(self) -> None:
        self.executor._user32.WindowFromPoint.return_value = 0xABC
        self.executor._user32.GetAncestor.return_value = 0xABC
        self.executor._user32.SetForegroundWindow.return_value = True
        self.executor._last_target_hwnd = None

        self.executor.prepare_target(100, 200)
        self.executor._user32.SetForegroundWindow.assert_called_once()

        self.executor._user32.SetForegroundWindow.reset_mock()
        self.executor.prepare_target(100, 200)
        self.executor._user32.SetForegroundWindow.assert_not_called()

    def test_click_calls_split_operations(self) -> None:
        self.executor._user32.WindowFromPoint.return_value = 0xABC
        self.executor._user32.GetAncestor.return_value = 0xABC
        self.executor._user32.SetForegroundWindow.return_value = True
        self.executor._user32.SetCursorPos.return_value = True
        self.executor._user32.GetCursorPos.return_value = True
        self.executor._user32.SendInput.return_value = 1

        with (
            patch.object(self.executor, "prepare_target") as mock_prep,
            patch.object(self.executor, "move_to") as mock_move,
            patch.object(self.executor, "mouse_down") as mock_down,
            patch.object(self.executor, "mouse_up") as mock_up,
        ):
            self.executor.click(100, 200)
            mock_prep.assert_called_once_with(100, 200, force=True)
            mock_move.assert_called_once_with(100, 200)
            mock_down.assert_called_once_with("left")
            mock_up.assert_called_once_with("left")


if __name__ == "__main__":
    unittest.main()
