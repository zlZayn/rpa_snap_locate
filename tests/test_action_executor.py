import ctypes
import unittest
from unittest.mock import Mock, patch

from core.action_executor import ActionExecutor, INPUT


class ActionExecutorSendInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = ActionExecutor.__new__(ActionExecutor)
        self.executor._user32 = Mock()

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


if __name__ == "__main__":
    unittest.main()
