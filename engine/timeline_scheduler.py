import logging
import time
from typing import Callable

logger = logging.getLogger("rpa_snap_locate.timeline_scheduler")


class TimelineScheduler:
    def __init__(self, late_warning_ms: float = 10.0):
        self._late_warning_ms = late_warning_ms
        self._replay_origin: int = 0
        self.lateness_ns: list[tuple[int, int, int]] = []
        self.executions: list[dict] = []

    @property
    def is_degraded(self) -> bool:
        if not self.lateness_ns:
            return False
        return any(
            late > self._late_warning_ms * 1_000_000 for _, _, late in self.lateness_ns
        )

    def run(
        self,
        events: list[dict],
        prepare_fn: Callable[[dict], None],
        down_fn: Callable[[str], None],
        up_fn: Callable[[str], None],
        screenshot_fn: Callable[[dict], None] | None = None,
        after_event_fn: Callable[[dict], None] | None = None,
    ) -> dict:
        self.lateness_ns.clear()
        self.executions.clear()

        # Prepare the first target before the clock starts so offset zero means
        # the first injected input, not locator/window setup time.
        first_prepared_index: int | None = None
        if events and events[0]["type"] == "mouse_down":
            prepare_fn(events[0])
            first_prepared_index = events[0]["index"]

        self._replay_origin = time.perf_counter_ns()
        pressed_buttons: set[str] = set()

        logger.info(
            "timeline start: %d events, replay_origin=%d",
            len(events),
            self._replay_origin,
        )

        try:
            for event in events:
                offset_ns = event["offset_ns"]
                deadline = self._replay_origin + offset_ns
                button = event.get("button", "left")

                if (
                    event["type"] == "mouse_down"
                    and event["index"] != first_prepared_index
                ):
                    prepare_fn(event)

                now = time.perf_counter_ns()
                wait_ns = deadline - now
                if wait_ns > 1_000_000:
                    time.sleep((wait_ns - 1_000_000) / 1_000_000_000)

                while time.perf_counter_ns() < deadline:
                    pass

                # This timestamp is immediately before SendInput dispatch.
                # Preparation time is therefore included whenever it causes
                # the event to miss its deadline.
                actual = time.perf_counter_ns()
                late = max(0, actual - deadline)

                if event["type"] == "mouse_down":
                    down_fn(button)
                    pressed_buttons.add(button)
                elif event["type"] == "mouse_up":
                    up_fn(button)
                    pressed_buttons.discard(button)
                elif event["type"] == "screenshot":
                    if screenshot_fn is not None:
                        screenshot_fn(event)
                else:
                    raise ValueError(f"unsupported timeline event: {event['type']}")

                if after_event_fn is not None:
                    after_event_fn(event)

                self.executions.append(
                    {
                        "index": event["index"],
                        "planned_offset_ns": offset_ns,
                        "actual_offset_ns": actual - self._replay_origin,
                        "lateness_ns": late,
                    }
                )
                if late > 0:
                    self.lateness_ns.append((event["index"], offset_ns, late))
                    if late > self._late_warning_ms * 1_000_000:
                        logger.warning(
                            "event %d late by %.2f ms (offset_ns=%d)",
                            event["index"],
                            late / 1_000_000,
                            offset_ns,
                        )
        finally:
            for button in tuple(pressed_buttons):
                try:
                    up_fn(button)
                    logger.warning(
                        "released mouse button %s after interrupted timeline", button
                    )
                    print(
                        f"[rpa] 回放中断，已自动释放鼠标按键 {button}。"
                    )
                except Exception:
                    logger.exception(
                        "failed to release mouse button %s after interruption", button
                    )
                    print(
                        f"[rpa] 回放中断，释放鼠标按键 {button} 失败，请手动点击一下鼠标。"
                    )

        total_ns = time.perf_counter_ns() - self._replay_origin
        total = len(events)
        late_events = [x for x in self.lateness_ns if x[2] > 0]
        late_count = len(late_events)
        status = "degraded" if self.is_degraded else "nominal"
        logger.info(
            "timeline complete: %d events, %d late (%s)",
            total,
            late_count,
            status,
        )
        return {
            "status": status,
            "total_events": total,
            "late_count": late_count,
            "total_wall_ns": total_ns,
            "lateness_ns": late_events,
            "executions": self.executions,
        }
