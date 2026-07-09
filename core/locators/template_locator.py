from core.locator_protocol import BaseLocator


class ScreenshotLocator(BaseLocator):
    def locate(self, step: dict) -> tuple[int, int]:
        region = step["region"]
        x = region["left"] + step["offset_x"]
        y = region["top"] + step["offset_y"]
        return (x, y)