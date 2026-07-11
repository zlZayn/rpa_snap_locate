import keyboard
import logging
from typing import Callable

logger = logging.getLogger("rpa_snap_locate.hotkey_registry")


class HotkeyRegistry:
    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register(self, hotkey: str, callback: Callable) -> None:
        hotkey_lower = hotkey.lower()
        self._handlers[hotkey_lower] = callback
        keyboard.add_hotkey(hotkey_lower, callback)
        logger.info("registered hotkey: %s", hotkey)

    def start_listening(self) -> None:
        logger.info("hotkey listener started")
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            logger.info("hotkey listener stopped by user")

    def remove_all(self) -> None:
        keyboard.unhook_all()
        self._handlers.clear()
