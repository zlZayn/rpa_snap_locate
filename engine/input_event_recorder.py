import logging
import queue
import threading
import time
from typing import Callable

import mouse

from core.perception_provider import PerceptionProvider
from utils.dpi_calculator import phys_to_normalized

logger = logging.getLogger("rpa_snap_locate.input_event_recorder")

_BUTTON_MAP = {
    "left": "left",
    "right": "right",
    "middle": "middle",
    "x": "x1",
    "x2": "x2",
}
_SUPPORTED_BUTTONS = {"left", "right", "middle"}


class InputRecordingError(RuntimeError):
    """Raised when a recording cannot be saved without losing input events."""


class InputEventRecorder:
    def __init__(
        self,
        queue_limit: int = 10_000,
    ):
        self._perception = PerceptionProvider()
        self._origin: int | None = None
        self._queue_limit = max(1, int(queue_limit))
        self._event_queue: queue.Queue = queue.Queue(maxsize=self._queue_limit)
        self._hook: Callable | None = None
        self._recording = False
        self._lock = threading.Lock()
        self._event_counter = 0
        self._last_x: int = 0
        self._last_y: int = 0
        self._capture_error: str | None = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        # Capture the segment origin as soon as the F2 callback enters the
        # recorder. Cursor lookup and hook setup are part of recording startup,
        # so the user's wait before the first business event is preserved.
        started_ns = time.perf_counter_ns()
        initial_x, initial_y = self._perception.get_mouse_position()
        with self._lock:
            if self._recording:
                return
            self._origin = started_ns
            self._event_counter = 0
            self._event_queue = queue.Queue(maxsize=self._queue_limit)
            self._last_x = initial_x
            self._last_y = initial_y
            self._capture_error = None
            self._recording = True
            logger.debug("recording started; segment_origin=%d", self._origin)

        self._hook = mouse.hook(self._on_mouse_event)

    def stop_recording(self) -> list[dict]:
        if self._hook:
            mouse.unhook(self._hook)
            self._hook = None

        with self._lock:
            self._recording = False
            raw_events: list[dict] = []
            while True:
                try:
                    raw_events.append(self._event_queue.get_nowait())
                except queue.Empty:
                    break
            capture_error = self._capture_error

        workflow_events = self._build_workflow_events(raw_events)
        with self._lock:
            self._origin = None
            self._event_counter = 0
            self._capture_error = None
        logger.debug(
            "recording stopped: %d raw events -> %d workflow events",
            len(raw_events),
            len(workflow_events),
        )
        if capture_error:
            raise InputRecordingError(capture_error)
        return workflow_events

    def cancel_recording(self) -> None:
        if self._hook:
            mouse.unhook(self._hook)
            self._hook = None
        with self._lock:
            self._recording = False
            self._origin = None
            self._event_counter = 0
            self._event_queue = queue.Queue(maxsize=self._queue_limit)
            self._capture_error = None
        logger.debug("recording cancelled")

    def capture_screenshot(self, region: dict) -> None:
        now_ns = time.perf_counter_ns()
        with self._lock:
            if not self._recording:
                return
            assert self._origin is not None
            offset_ns = now_ns - self._origin
            if offset_ns < 0:
                offset_ns = 0
            raw_event = {
                "type": "screenshot",
                "region": dict(region),
                "offset_ns": offset_ns,
            }
            try:
                self._event_queue.put_nowait(raw_event)
            except queue.Full:
                self._capture_error = (
                    f"input event queue exceeded limit {self._queue_limit}; "
                    "recording is incomplete"
                )

    def _on_mouse_event(self, event) -> None:
        now_ns = time.perf_counter_ns()

        if isinstance(event, mouse.MoveEvent):
            with self._lock:
                self._last_x = event.x
                self._last_y = event.y
            return

        if isinstance(event, mouse.ButtonEvent):
            # On Windows the mouse package replaces the second DOWN of a
            # double-click with DOUBLE. It is not an extra semantic event: for
            # a lossless down/up timeline it must be stored as another down.
            event_type = "down" if event.event_type == "double" else event.event_type
            with self._lock:
                if not self._recording:
                    return
                assert self._origin is not None
                button = _BUTTON_MAP.get(event.button, event.button)
                if button not in _SUPPORTED_BUTTONS:
                    self._capture_error = f"unsupported mouse button recorded: {button}"
                    return
                offset_ns = now_ns - self._origin
                if offset_ns < 0:
                    offset_ns = 0

                self._event_counter += 1
                raw_event = {
                    "raw_index": self._event_counter,
                    "type": event_type,
                    "button": button,
                    "offset_ns": offset_ns,
                    "x": self._last_x,
                    "y": self._last_y,
                }
                try:
                    self._event_queue.put_nowait(raw_event)
                except queue.Full:
                    self._capture_error = (
                        f"input event queue exceeded limit {self._queue_limit}; "
                        "recording is incomplete"
                    )

    def _build_workflow_events(self, raw_events: list[dict]) -> list[dict]:
        workflow_events: list[dict] = []
        pending_down_by_button: dict[str, int] = {}

        window_info = self._perception.get_active_window()
        dpi_scale = self._perception.get_dpi_scale()
        logical_w, logical_h = self._perception.get_logical_resolution()

        for i, raw in enumerate(raw_events):
            idx = i + 1
            if raw["type"] == "screenshot":
                event = {
                    "index": idx,
                    "type": "screenshot",
                    "region": raw["region"],
                    "offset_ns": raw["offset_ns"],
                }
                workflow_events.append(event)

            elif raw["type"] == "down":
                norm_x, norm_y = phys_to_normalized(
                    raw["x"],
                    raw["y"],
                    logical_w,
                    logical_h,
                    dpi_scale,
                )
                event = {
                    "index": idx,
                    "type": "mouse_down",
                    "button": raw["button"],
                    "offset_ns": raw["offset_ns"],
                    "method": "fixed",
                    "norm_x": round(norm_x, 6),
                    "norm_y": round(norm_y, 6),
                    "window_title": window_info["title"],
                    "dpi_scale": dpi_scale,
                }
                pending_down_by_button[raw["button"]] = idx
                workflow_events.append(event)

            elif raw["type"] == "up":
                event = {
                    "index": idx,
                    "type": "mouse_up",
                    "button": raw["button"],
                    "offset_ns": raw["offset_ns"],
                    "position_from_event": pending_down_by_button.pop(
                        raw["button"], idx
                    ),
                }
                workflow_events.append(event)

        return workflow_events
