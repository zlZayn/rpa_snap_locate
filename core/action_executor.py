import ctypes
from ctypes import wintypes
import logging

import pyautogui

pyautogui.FAILSAFE = False

logger = logging.getLogger("rpa_snap_locate.action_executor")


if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_ulonglong
else:
    ULONG_PTR = ctypes.c_ulong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class INPUT_UNION(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT),)


class INPUT(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = (
        ("type", wintypes.DWORD),
        ("data", INPUT_UNION),
    )


INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
GA_ROOT = 2

_BUTTON_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


class ActionExecutor:
    def __init__(self):
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._declare_win32_signatures()
        self._last_target_hwnd = None

    def _declare_win32_signatures(self) -> None:
        self._user32.WindowFromPoint.argtypes = (wintypes.POINT,)
        self._user32.WindowFromPoint.restype = wintypes.HWND
        self._user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
        self._user32.GetAncestor.restype = wintypes.HWND
        self._user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
        self._user32.SetForegroundWindow.restype = wintypes.BOOL
        self._user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
        self._user32.SetCursorPos.restype = wintypes.BOOL
        self._user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
        self._user32.GetCursorPos.restype = wintypes.BOOL
        self._user32.SendInput.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        )
        self._user32.SendInput.restype = wintypes.UINT
        self._kernel32.GetConsoleWindow.argtypes = ()
        self._kernel32.GetConsoleWindow.restype = wintypes.HWND

    def prepare_target(self, x: int, y: int, force: bool = False) -> int:
        point = wintypes.POINT(x, y)
        child_hwnd = self._user32.WindowFromPoint(point)
        target_hwnd = (
            self._user32.GetAncestor(child_hwnd, GA_ROOT) if child_hwnd else None
        )
        if not target_hwnd:
            return 0

        if not force and target_hwnd == self._last_target_hwnd:
            return target_hwnd

        console_hwnd = self._kernel32.GetConsoleWindow()
        if target_hwnd != console_hwnd:
            if not self._user32.SetForegroundWindow(target_hwnd):
                logger.warning(
                    "could not foreground target window 0x%x",
                    target_hwnd,
                )

        self._last_target_hwnd = target_hwnd
        return target_hwnd

    def move_to(self, x: int, y: int) -> None:
        ctypes.set_last_error(0)
        if not self._user32.SetCursorPos(x, y):
            error = ctypes.get_last_error()
            raise OSError(
                error,
                "SetCursorPos failed; the process may not be attached to the active "
                "interactive desktop",
            )

        actual = wintypes.POINT()
        if not self._user32.GetCursorPos(ctypes.byref(actual)):
            raise ctypes.WinError(ctypes.get_last_error())
        if (actual.x, actual.y) != (x, y):
            raise RuntimeError(
                f"cursor was constrained to ({actual.x}, {actual.y}); "
                f"requested ({x}, {y})"
            )

    def mouse_down(self, button: str = "left") -> None:
        if button not in _BUTTON_FLAGS:
            raise ValueError(f"unsupported mouse button: {button}")
        down_flag, _ = _BUTTON_FLAGS[button]
        self._send_mouse_button(down_flag)

    def mouse_up(self, button: str = "left") -> None:
        if button not in _BUTTON_FLAGS:
            raise ValueError(f"unsupported mouse button: {button}")
        _, up_flag = _BUTTON_FLAGS[button]
        self._send_mouse_button(up_flag)

    def click(self, x: int, y: int) -> None:
        self.prepare_target(x, y, force=True)
        self.move_to(x, y)
        self.mouse_down("left")
        self.mouse_up("left")
        logger.info("clicked at (%d, %d)", x, y)

    def _send_mouse_button(self, flag: int) -> None:
        event = INPUT(
            type=INPUT_MOUSE,
            data=INPUT_UNION(mi=MOUSEINPUT(dwFlags=flag)),
        )
        ctypes.set_last_error(0)
        inserted = self._user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
        if inserted != 1:
            error = ctypes.get_last_error()
            detail = f"Win32 error {error}" if error else "no Win32 error was reported"
            raise PermissionError(
                "SendInput was rejected ("
                + detail
                + "). Windows UIPI blocks simulated input into a window running "
                "at a higher integrity level. Run the RPA process and target app "
                "with the same privileges (preferably both non-administrator)."
            )

    def type_text(self, text: str) -> None:
        pyautogui.write(text, interval=0.05)
        logger.info("typed text (%d chars)", len(text))
