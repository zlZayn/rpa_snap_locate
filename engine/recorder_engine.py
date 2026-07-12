import logging
import threading
from enum import Enum
from typing import Optional
from config.config_manager import ConfigManager
from core.perception_provider import PerceptionProvider
from data.data_manager import DataManager
from engine.input_event_recorder import InputEventRecorder, InputRecordingError
from engine.step_builder import StepBuilder

logger = logging.getLogger("rpa_snap_locate.recorder_engine")


class RecorderState(Enum):
    IDLE = "IDLE"
    RECORDING = "RECORDING"
    RECORDING_WAITING_SECOND = "RECORDING_WAITING_SECOND"
    WAITING_SECOND = "WAITING_SECOND"
    WAITING_TARGET = "WAITING_TARGET"


class RecorderEngine:
    def __init__(self):
        self._config = ConfigManager()
        self._perception = PerceptionProvider()
        self._data_manager = DataManager()
        self._step_builder = StepBuilder()
        self._mode = self._config.get("recorder", "mode", default="timeline")
        self._input_recorder = InputEventRecorder(
            queue_limit=self._config.get(
                "recorder", "event_queue_limit", default=10_000
            ),
        )
        self.state = RecorderState.IDLE
        self._steps: list[dict] = []
        self._events: list[dict] = []
        self._box_point1: Optional[tuple[int, int]] = None
        self._box_point2: Optional[tuple[int, int]] = None
        self._box_region: Optional[dict] = None
        self._cancel_event = threading.Event()
        self._ts = self._data_manager.new_ts()
        self._last_saved_path: str | None = None

    @property
    def is_timeline_mode(self) -> bool:
        return self._mode == "timeline"

    @property
    def steps(self) -> list[dict]:
        return list(self._steps)

    @property
    def step_count(self) -> int:
        return len(self._steps)

    @property
    def recorded_action_count(self) -> int:
        if self.is_timeline_mode:
            return sum(event.get("type") == "mouse_down" for event in self._events)
        return len(self._steps)

    @property
    def has_unsaved_actions(self) -> bool:
        if self.is_timeline_mode:
            return self._input_recorder.is_recording or bool(self._events)
        return bool(self._steps)

    @property
    def last_saved_path(self) -> str | None:
        return self._last_saved_path

    def on_f2(self) -> str:
        if self.is_timeline_mode:
            return self._timeline_f2()
        return self._legacy_f2()

    def on_f3(self) -> str:
        if self.is_timeline_mode:
            return self._timeline_f3()
        return self._legacy_f3()

    def on_cancel(self) -> str:
        if self.is_timeline_mode:
            return self._timeline_cancel()
        return self._legacy_cancel()

    def save(self) -> str:
        if self.is_timeline_mode:
            return self._timeline_save()
        return self._legacy_save()

    def clear(self) -> str:
        if self.is_timeline_mode:
            return self._timeline_clear()
        return self._legacy_clear()

    # --- Timeline mode ---

    def _timeline_f2(self) -> str:
        recording_states = {
            RecorderState.RECORDING,
            RecorderState.RECORDING_WAITING_SECOND,
        }
        if self.state in recording_states:
            try:
                self._append_timeline_events(
                    self._input_recorder.stop_recording()
                )
            except (InputRecordingError, ValueError) as exc:
                logger.debug("recording stopped with data loss: %s", exc)
                self.state = RecorderState.IDLE
                self._box_point1 = None
                self._box_point2 = None
                return f"recording failed: {exc}"
            self.state = RecorderState.IDLE
            self._box_point1 = None
            self._box_point2 = None
            logger.debug("F2: recording stopped")
            return "recording stopped"
        else:
            self._input_recorder.start_recording()
            self.state = RecorderState.RECORDING
            logger.debug("F2: recording started")
            return "recording started"

    def _timeline_f3(self) -> str:
        if self.state == RecorderState.RECORDING:
            self._box_point1 = self._perception.get_mouse_position()
            self.state = RecorderState.RECORDING_WAITING_SECOND
            self._cancel_event.clear()
            logger.debug("F3: first corner at %s", self._box_point1)
            return "first corner recorded, move mouse and press F3 again"
        elif self.state == RecorderState.RECORDING_WAITING_SECOND:
            self._box_point2 = self._perception.get_mouse_position()
            assert self._box_point1 is not None
            assert self._box_point2 is not None
            x1, y1 = self._box_point1
            x2, y2 = self._box_point2
            left, top = min(x1, x2), min(y1, y2)
            right, bottom = max(x1, x2), max(y1, y2)
            width, height = right - left, bottom - top
            region = {"left": left, "top": top, "width": width, "height": height}
            self._input_recorder.capture_screenshot(region)
            self._box_point1 = None
            self._box_point2 = None
            self.state = RecorderState.RECORDING
            logger.debug("F3: screenshot event queued for region %s", region)
            return "box selection complete. Capture region recorded."
        else:
            return "cannot press F3 in current state"

    def _timeline_cancel(self) -> str:
        if self.state == RecorderState.RECORDING_WAITING_SECOND:
            self.state = RecorderState.RECORDING
            self._box_point1 = None
            self._box_point2 = None
            self._cancel_event.set()
            logger.debug("box selection cancelled")
            return "box selection cancelled"
        elif self.state == RecorderState.RECORDING:
            return "no box selection to cancel"
        else:
            return "no active operation to cancel"

    def _timeline_save(self) -> str:
        if self.state in {
            RecorderState.RECORDING,
            RecorderState.RECORDING_WAITING_SECOND,
        }:
            try:
                self._append_timeline_events(
                    self._input_recorder.stop_recording()
                )
            except (InputRecordingError, ValueError) as exc:
                self.state = RecorderState.IDLE
                logger.debug("save failed because recording is incomplete: %s", exc)
                return f"save failed: {exc}"
            self.state = RecorderState.IDLE
            self._box_point1 = None
            self._box_point2 = None

        if not self._events:
            return "no events to save"

        name = self._prompt_name()
        events_to_save = list(self._events)
        saved_count = len(events_to_save)
        try:
            path = self._data_manager.save_workflow_v5(
                events_to_save,
                self._ts,
                name,
            )
            self._last_saved_path = path
            self._reset_recording()
            logger.debug(
                "saved %d events to %s, recording reset",
                saved_count,
                path,
            )
            return (
                f"saved {saved_count} events to {path}. "
                f"Recording reset, ready for new workflow."
            )
        except ValueError as e:
            logger.debug("save failed: %s", e)
            return f"save failed: {e}"

    def _timeline_clear(self) -> str:
        self._input_recorder.cancel_recording()
        self._reset_recording(refresh_ts=False)
        logger.debug("workflow cleared")
        return "workflow cleared"

    def _append_timeline_events(self, events: list[dict]) -> None:
        """Append a recording segment without duplicate indices or time origins."""
        if not events:
            return

        base_index = len(self._events)
        base_offset = self._events[-1]["offset_ns"] if self._events else 0
        index_map: dict[int, int] = {}
        appended: list[dict] = []

        for position, source in enumerate(events, start=1):
            event = dict(source)
            old_index = event["index"]
            new_index = base_index + position
            index_map[old_index] = new_index
            event["index"] = new_index
            event["offset_ns"] = base_offset + event["offset_ns"]
            if event["type"] == "mouse_up":
                old_down = event["position_from_event"]
                if old_down not in index_map:
                    raise ValueError(
                        f"mouse_up event references unavailable down event {old_down}"
                    )
                event["position_from_event"] = index_map[old_down]
            appended.append(event)

        self._events.extend(appended)

    # --- Legacy mode ---

    def _legacy_f2(self) -> str:
        if self.state == RecorderState.WAITING_TARGET:
            return self._handle_f2_in_box()
        step = self._step_builder.build_fixed_click_step()
        self._steps.append(step)
        logger.debug(
            "F2: recorded fixed click step %d at (%.4f, %.4f)",
            step["index"],
            step["norm_x"],
            step["norm_y"],
        )
        return f"recorded click step {step['index']}"

    def _legacy_f3(self) -> str:
        if self.state == RecorderState.IDLE:
            return self._handle_f3_first()
        elif self.state == RecorderState.WAITING_SECOND:
            return self._handle_f3_second()
        else:
            return "cannot press F3 in current state"

    def _legacy_cancel(self) -> str:
        if self.state == RecorderState.IDLE:
            return "no active operation to cancel"
        self.state = RecorderState.IDLE
        self._box_point1 = None
        self._box_point2 = None
        self._box_region = None
        self._cancel_event.set()
        logger.debug("box selection cancelled")
        return "box selection cancelled"

    def _legacy_save(self) -> str:
        if not self._steps:
            return "no steps to save"
        name = self._prompt_name()
        steps_to_save = list(self._steps)
        saved_count = len(steps_to_save)
        path = self._data_manager.save_workflow(steps_to_save, self._ts, name)
        self._last_saved_path = path
        self._reset_recording()
        logger.debug(
            "saved %d steps to %s, recording reset for new workflow",
            saved_count,
            path,
        )
        return (
            f"saved {saved_count} steps to {path}. "
            f"Recording reset, ready for new workflow."
        )

    def _legacy_clear(self) -> str:
        self._reset_recording(refresh_ts=False)
        logger.debug("workflow cleared")
        return "workflow cleared"

    # --- Shared helpers ---

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
        self._events.clear()
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
        logger.debug("box select: first corner at %s", self._box_point1)
        return "first corner recorded, move mouse to opposite corner and press F3 again"

    def _handle_f3_second(self) -> str:
        self._box_point2 = self._perception.get_mouse_position()
        assert self._box_point1 is not None
        assert self._box_point2 is not None
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
        step = self._step_builder.build_absolute_click_step(mouse_x, mouse_y)
        self._steps.append(step)
        self.state = RecorderState.IDLE
        self._box_point1 = None
        self._box_point2 = None
        self._box_region = None
        logger.debug(
            "F2 in box: recorded fixed click step %d at (%d, %d)",
            step["index"],
            mouse_x,
            mouse_y,
        )
        return f"recorded click step {step['index']}"

    def use_box_center(self) -> str:
        if (
            self.state != RecorderState.WAITING_TARGET
            or self._box_region is None
        ):
            return "not in box target state"
        region = self._box_region
        phys_x = region["left"] + region["width"] // 2
        phys_y = region["top"] + region["height"] // 2
        step = self._step_builder.build_absolute_click_step(phys_x, phys_y)
        self._steps.append(step)
        self.state = RecorderState.IDLE
        self._box_point1 = None
        self._box_point2 = None
        self._box_region = None
        logger.debug(
            "box center: recorded fixed click step %d at (%d, %d)",
            step["index"],
            phys_x,
            phys_y,
        )
        return f"recorded click step {step['index']} with box center"
