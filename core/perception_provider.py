import mss
import pygetwindow as gw
import pyautogui
from PIL import Image
from config.config_manager import ConfigManager
from utils.dpi_calculator import get_system_dpi_scale


class PerceptionProvider:
    def __init__(self):
        self._sct = mss.mss()
        self._config = ConfigManager()

    def capture_screen(self) -> Image.Image:
        monitor = self._sct.monitors[1]
        sct_img = self._sct.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.rgb)

    def capture_region(
        self, left: int, top: int, width: int, height: int
    ) -> Image.Image:
        region = {"left": left, "top": top, "width": width, "height": height}
        sct_img = self._sct.grab(region)
        return Image.frombytes("RGB", sct_img.size, sct_img.rgb)

    def get_mouse_position(self) -> tuple[int, int]:
        return pyautogui.position()

    def get_active_window(self) -> dict:
        window = gw.getActiveWindow()
        if window is None:
            return {
                "title": "",
                "hwnd": 0,
                "left": 0,
                "top": 0,
                "width": 0,
                "height": 0,
            }
        return {
            "title": window.title,
            "hwnd": window._hWnd,
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
        }

    def get_dpi_scale(self) -> float:
        configured = self._config.get("screen", "dpi_scale", default="auto")
        if configured != "auto":
            return float(configured)
        return get_system_dpi_scale()

    def get_logical_resolution(self) -> tuple[int, int]:
        configured_w = self._config.get("screen", "logical_width", default=0)
        configured_h = self._config.get("screen", "logical_height", default=0)
        if configured_w and configured_h:
            return (int(configured_w), int(configured_h))
        dpi = self.get_dpi_scale()
        w = pyautogui.size().width
        h = pyautogui.size().height
        logical_w = int(w / dpi)
        logical_h = int(h / dpi)
        return (logical_w, logical_h)
