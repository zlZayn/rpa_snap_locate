from core.locator_protocol import BaseLocator


class LLMLocator(BaseLocator):
    def locate(self, step: dict) -> tuple[int, int]:
        raise NotImplementedError("LLM定位器尚未实现")