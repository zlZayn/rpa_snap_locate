from core.perception_provider import PerceptionProvider
from utils.dpi_calculator import phys_to_normalized


class StepBuilder:
    def __init__(self):
        self._perception = PerceptionProvider()
        self._step_counter = 0

    def reset_counter(self) -> None:
        self._step_counter = 0

    def build_fixed_click_step(self) -> dict:
        self._step_counter += 1
        phys_x, phys_y = self._perception.get_mouse_position()
        window_info = self._perception.get_active_window()
        dpi_scale = self._perception.get_dpi_scale()
        logical_w, logical_h = self._perception.get_logical_resolution()
        norm_x, norm_y = phys_to_normalized(
            phys_x, phys_y, logical_w, logical_h, dpi_scale
        )
        return {
            "index": self._step_counter,
            "action": "click",
            "method": "fixed",
            "norm_x": round(norm_x, 6),
            "norm_y": round(norm_y, 6),
            "window_title": window_info["title"],
            "dpi_scale": dpi_scale,
        }

    def build_screenshot_click_step(
        self,
        region: dict,
        offset_x: int,
        offset_y: int,
    ) -> dict:
        self._step_counter += 1
        window_info = self._perception.get_active_window()
        dpi_scale = self._perception.get_dpi_scale()
        return {
            "index": self._step_counter,
            "action": "click",
            "method": "screenshot",
            "region": region,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "window_title": window_info["title"],
            "dpi_scale": dpi_scale,
        }
