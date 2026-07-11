from abc import ABC, abstractmethod


class BaseLocator(ABC):
    @abstractmethod
    def locate(self, step: dict) -> tuple[int, int]: ...


def create_locator(method: str) -> BaseLocator:
    from core.locators import FixedLocator, LLMLocator

    mapping = {
        "fixed": FixedLocator,
        "llm": LLMLocator,
    }
    cls = mapping.get(method)
    if cls is None:
        raise ValueError(f"unknown locator method: {method}")
    return cls()
