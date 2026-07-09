import pyautogui
import time
import logging

pyautogui.FAILSAFE = False

logger = logging.getLogger("rpa_snap_locate.action_executor")


class ActionExecutor:
    def click(self, x: int, y: int) -> None:
        pyautogui.click(x, y)
        logger.info("clicked at (%d, %d)", x, y)

    def type_text(self, text: str) -> None:
        pyautogui.write(text, interval=0.05)
        logger.info("typed text (%d chars)", len(text))