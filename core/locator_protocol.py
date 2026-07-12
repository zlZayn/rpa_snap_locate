from abc import ABC, abstractmethod


class BaseLocator(ABC):
    @abstractmethod
    def locate(self, step: dict) -> tuple[int, int]: ...


def create_locator(method: str) -> BaseLocator:
    from core.locators import FixedLocator

    mapping = {
        "fixed": FixedLocator,
    }
    cls = mapping.get(method)
    if cls is None:
        raise ValueError(f"unknown locator method: {method}")
    return cls()
