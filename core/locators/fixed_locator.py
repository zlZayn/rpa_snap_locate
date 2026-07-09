from core.locator_protocol import BaseLocator
from core.perception_provider import PerceptionProvider
from utils.dpi_calculator import normalized_to_phys


class FixedLocator(BaseLocator):
    def __init__(self):
        self._perception = PerceptionProvider()

    def locate(self, step: dict) -> tuple[int, int]:
        norm_x = step["norm_x"]
        norm_y = step["norm_y"]
        logical_w, logical_h = self._perception.get_logical_resolution()
        dpi_scale = self._perception.get_dpi_scale()
        return normalized_to_phys(norm_x, norm_y, logical_w, logical_h, dpi_scale)