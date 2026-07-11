import logging
import threading
from enum import Enum
from typing import Optional
from config.config_manager import ConfigManager
from core.perception_provider import PerceptionProvider
from data.data_manager import DataManager
from engine.step_builder import StepBuilder

logger = logging.getLogger("rpa_snap_locate.recorder_engine")


class RecorderState(Enum):
    IDLE = "IDLE"
    WAITING_SECOND = "WAITING_SECOND"
    WAITING_TARGET = "WAITING_TARGET"


class RecorderEngine:
    def __init__(self):
        self._config = ConfigManager()
        self._perception = PerceptionProvider()
        self._data_manager = DataManager()
        self._step_builder = StepBuilder()
        self.state = RecorderState.IDLE
        self._steps: list[dict] = []
        self._box_point1: Optional[tuple[int, int]] = None
        self._box_point2: Optional[tuple[int, int]] = None
        self._box_region: Optional[dict] = None
        self._cancel_event = threading.Event()
        self._timeout_seconds = self._config.get(
            "recorder", "box_select_timeout_seconds", default=10
        )
        self._ts = self._data_manager.new_ts()

    @property
    def steps(self) -> list[dict]:
        return list(self._steps)

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def on_f2(self) -> str:
        if self.state == RecorderState.WAITING_TARGET:
            return self._handle_f2_in_box()
        step = self._step_builder.build_fixed_click_step()
        self._steps.append(step)
        logger.info(
            "F2: recorded fixed click step %d at (%.4f, %.4f)",
            step["index"], step["norm_x"], step["norm_y"],
        )
        return f"recorded click step {step['index']}"

    def on_f3(self) -> str:
        if self.state == RecorderState.IDLE:
            return self._handle_f3_first()
        elif self.state == RecorderState.WAITING_SECOND:
            return self._handle_f3_second()
        else:
            return "cannot press F3 in current state"

    def on_cancel(self) -> str:
        if self.state == RecorderState.IDLE:
            return "no active operation to cancel"
        self.state = RecorderState.IDLE
        self._box_point1 = None
        self._box_point2 = None
        self._box_region = None
        self._cancel_event.set()
        logger.info("box selection cancelled")
        return "box selection cancelled"

    def save(self) -> str:
        if not self._steps:
            return "no steps to save"

        name = self._prompt_name()
        steps_to_save = list(self._steps)
        saved_count = len(steps_to_save)
        path = self._data_manager.save_workflow(steps_to_save, self._ts, name)
        self._reset_recording()
        logger.info(
            "saved %d steps to %s, recording reset for new workflow",
            saved_count, path,
        )
        return (
            f"saved {saved_count} steps to {path}. "
            f"Recording reset, ready for new workflow."
        )

    def clear(self) -> str:
        self._reset_recording(refresh_ts=False)
        logger.info("workflow cleared")
        return "workflow cleared"

    def _prompt_name(self) -> str:
        try:
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            result = simpledialog.askstring(
                "Save Workflow",
                "Workflow name (optional):",
                parent=root,
            )
            root.destroy()
            return (result or "").strip()
        except Exception:
            return ""

    def _reset_recording(self, refresh_ts: bool = True) -> None:
        self._steps.clear()
        self._step_builder.reset_counter()
        self.state = RecorderState.IDLE
        self._box_point1 = None
        self._box_point2 = None
        self._box_region = None
        if refresh_ts:
            self._ts = self._data_manager.new_ts()

    def _handle_f3_first(self) -> str:
        self._box_point1 = self._perception.get_mouse_position()
        self.state = RecorderState.WAITING_SECOND
        self._cancel_event.clear()
        logger.info("box select: first corner at %s", self._box_point1)
        return "first corner recorded, move mouse to opposite corner and press F3 again"

    def _handle_f3_second(self) -> str:
        self._box_point2 = self._perception.get_mouse_position()
        x1, y1 = self._box_point1
        x2, y2 = self._box_point2
        left, top = min(x1, x2), min(y1, y2)
        right, bottom = max(x1, x2), max(y1, y2)
        width, height = right - left, bottom - top
        self._box_region = {"left": left, "top": top, "width": width, "height": height}

        self.state = RecorderState.WAITING_TARGET
        msg = (
            "box selection complete. "
            "Press F2 to set click target inside the box, "
            "or press ESC to use box center as default"
        )
        return msg

    def _handle_f2_in_box(self) -> str:
        mouse_x, mouse_y = self._perception.get_mouse_position()
        region = self._box_region
        offset_x = mouse_x - region["left"]
        offset_y = mouse_y - region["top"]
        step = self._step_builder.build_screenshot_click_step(
            region=region,
            offset_x=offset_x,
            offset_y=offset_y,
        )
        self._steps.append(step)
        self.state = RecorderState.IDLE
        self._box_point1 = None
        self._box_point2 = None
        self._box_region = None
        logger.info(
            "F2 in box: recorded screenshot click step %d at offset (%d, %d)",
            step["index"], offset_x, offset_y,
        )
        return f"recorded screenshot click step {step['index']}"

    def use_box_center(self) -> str:
        if self.state != RecorderState.WAITING_TARGET or self._box_region is None:
            return "not in box target state"
        region = self._box_region
        offset_x = region["width"] // 2
        offset_y = region["height"] // 2
        step = self._step_builder.build_screenshot_click_step(
            region=region,
            offset_x=offset_x,
            offset_y=offset_y,
        )
        self._steps.append(step)
        self.state = RecorderState.IDLE
        self._box_point1 = None
        self._box_point2 = None
        self._box_region = None
        logger.info(
            "box center: recorded screenshot click step %d at center (%d, %d)",
            step["index"], offset_x, offset_y,
        )
        return f"recorded screenshot click step {step['index']} with box center"
