import json
import logging
import os
from datetime import datetime
import time as _time
from PIL import ImageDraw
from core.locator_protocol import create_locator
from core.action_executor import ActionExecutor
from core.perception_provider import PerceptionProvider
from config.config_manager import ConfigManager
from engine.timeline_scheduler import TimelineScheduler
from engine.workflow_validator import validate_v5_events

logger = logging.getLogger("rpa_snap_locate.pipeline_runner")


class PipelineRunner:
    def __init__(self):
        self._perception = PerceptionProvider()
        self._config = ConfigManager()
        self._start_delay = self._config.get(
            "replay", "start_delay_seconds", default=0.0
        )

    def run(self, workflow_path: str) -> None:
        if not os.path.exists(workflow_path):
            logger.warning("workflow not found: %s", workflow_path)
            return
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        version = workflow.get("version", "4.0")
        if version == "5.0":
            self._run_v5(workflow, workflow_path)
        elif version == "4.0":
            self._run_v4(workflow, workflow_path)
        else:
            raise ValueError(f"unsupported workflow version: {version}")

    def _run_v4(self, workflow: dict, workflow_path: str) -> None:
        steps = workflow.get("steps", [])
        if not steps:
            logger.warning("workflow is empty, nothing to run")
            return

        if self._start_delay > 0:
            logger.info("starting pipeline in %.1f seconds ...", self._start_delay)
            _time.sleep(self._start_delay)

        run_dir = self._make_run_dir(workflow_path)
        screenshots_dir = os.path.join(run_dir, "screenshots")
        snapshots_dir = os.path.join(run_dir, "snapshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        os.makedirs(snapshots_dir, exist_ok=True)

        executor = ActionExecutor()
        for step in steps:
            idx = step["index"]
            method = step["method"]
            locator = create_locator(method)
            x, y = locator.locate(step)

            before = self._perception.capture_screen()
            executor.click(x, y)
            _time.sleep(0.3)
            after = self._perception.capture_screen()

            self._mark_click(before, x, y).save(
                os.path.join(snapshots_dir, f"step_{idx:04d}_before.png")
            )
            self._mark_click(after, x, y).save(
                os.path.join(snapshots_dir, f"step_{idx:04d}_after.png")
            )

            region = step.get("region")
            if region:
                region_img = self._perception.capture_region(
                    region["left"],
                    region["top"],
                    region["width"],
                    region["height"],
                )
                region_img.save(
                    os.path.join(screenshots_dir, f"step_{idx:04d}.png"), "PNG"
                )

            logger.info("step %d: clicked (%d, %d), snapshots saved", idx, x, y)

        logger.info(
            "pipeline complete: %d steps executed, run dir: %s",
            len(steps),
            run_dir,
        )

    def _run_v5(self, workflow: dict, workflow_path: str) -> None:
        events = workflow.get("events", [])
        if not events:
            logger.warning("workflow has no events, nothing to run")
            return
        validate_v5_events(events)

        if self._start_delay > 0:
            logger.info("starting timeline in %.1f seconds ...", self._start_delay)
            _time.sleep(self._start_delay)

        run_dir = self._make_run_dir(workflow_path)
        screenshots_dir = os.path.join(run_dir, "screenshots")
        snapshots_dir = os.path.join(run_dir, "snapshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        os.makedirs(snapshots_dir, exist_ok=True)

        executor = ActionExecutor()
        scheduler = TimelineScheduler(
            late_warning_ms=self._config.get("replay", "late_warning_ms", default=10.0),
        )

        resolved: dict[int, tuple[int, int]] = {}

        def prepare_down(event: dict) -> None:
            idx = event["index"]
            if idx in resolved:
                x, y = resolved[idx]
            else:
                method = event.get("method", "fixed")
                locator = create_locator(method)
                x, y = locator.locate(event)
                resolved[idx] = (x, y)
            before = self._perception.capture_screen()
            self._mark_click(before, x, y).save(
                os.path.join(snapshots_dir, f"event_{idx:04d}_before.png")
            )
            executor.prepare_target(x, y)
            executor.move_to(x, y)

        def mouse_down(button: str) -> None:
            executor.mouse_down(button)

        def mouse_up(button: str) -> None:
            executor.mouse_up(button)

        def after_event(event: dict) -> None:
            if event["type"] != "mouse_up":
                return
            down_idx = event.get("position_from_event")
            if down_idx is None or down_idx not in resolved:
                return
            _time.sleep(0.2)
            x, y = resolved[down_idx]
            after = self._perception.capture_screen()
            self._mark_click(after, x, y).save(
                os.path.join(snapshots_dir, f"event_{event['index']:04d}_after.png")
            )

        def on_screenshot(event: dict) -> None:
            region = event["region"]
            region_img = self._perception.capture_region(
                region["left"],
                region["top"],
                region["width"],
                region["height"],
            )
            if region_img:
                region_img.save(
                    os.path.join(
                        screenshots_dir, f"event_{event['index']:04d}.png"
                    ),
                    "PNG",
                )

        before_evidence = self._perception.capture_screen()
        report = scheduler.run(
            events, prepare_down, mouse_down, mouse_up,
            screenshot_fn=on_screenshot,
            after_event_fn=after_event,
        )
        after_evidence = self._perception.capture_screen()

        evidence_ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        report["evidence_captured_at"] = evidence_ts

        if before_evidence:
            before_evidence.save(os.path.join(snapshots_dir, "burst_before.png"))
        if after_evidence:
            after_evidence.save(os.path.join(snapshots_dir, "burst_after.png"))

        report_path = os.path.join(run_dir, "replay_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(
            "timeline complete: %d events, run dir: %s (%s)",
            len(events),
            run_dir,
            report["status"],
        )

    @staticmethod
    def _mark_click(image, x: int, y: int):
        img = image.copy()
        d = ImageDraw.Draw(img)
        r = 6
        d.ellipse([x - r, y - r, x + r, y + r], outline="red", width=3)
        d.line([x - r - 4, y, x + r + 4, y], fill="red", width=2)
        d.line([x, y - r - 4, x, y + r + 4], fill="red", width=2)
        return img

    def _make_run_dir(self, workflow_path: str) -> str:
        run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = os.path.basename(workflow_path)
        recordings_dir = self._config.get("paths", "recordings_dir")
        stem, ext = os.path.splitext(fname)
        if ext == ".json":
            run_dir = os.path.join(recordings_dir, stem, run_ts)
        else:
            run_dir = os.path.join(os.path.dirname(workflow_path), run_ts)
        os.makedirs(run_dir, exist_ok=True)
        return run_dir
