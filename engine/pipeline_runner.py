import json
import logging
import os
import re
from datetime import datetime
import time as _time
from PIL import ImageDraw
from core.locator_protocol import create_locator
from core.action_executor import ActionExecutor
from core.perception_provider import PerceptionProvider
from config.config_manager import ConfigManager

logger = logging.getLogger("rpa_snap_locate.pipeline_runner")


class PipelineRunner:
    def __init__(self):
        self._perception = PerceptionProvider()
        self._config = ConfigManager()
        self._start_delay = self._config.get("replay", "start_delay_seconds", default=0.0)

    def run(self, workflow_path: str) -> None:
        if not os.path.exists(workflow_path):
            logger.warning("workflow not found: %s", workflow_path)
            return
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        steps = workflow.get("steps", [])
        if not steps:
            logger.warning("workflow is empty, nothing to run")
            return

        if self._start_delay > 0:
            logger.info("starting pipeline in %.1f seconds ...", self._start_delay)
            _time.sleep(self._start_delay)

        run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = os.path.basename(workflow_path)
        m = re.match(r"^(\d{8}_\d{6}-\d+steps)\.json$", fname)
        if m:
            recordings_dir = self._config.get("paths", "recordings_dir")
            run_dir = os.path.join(recordings_dir, m.group(1), run_ts)
        else:
            run_dir = os.path.join(os.path.dirname(workflow_path), run_ts)

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

            def mark(image):
                img = image.copy()
                d = ImageDraw.Draw(img)
                r = 6
                d.ellipse([x - r, y - r, x + r, y + r], outline="red", width=3)
                d.line([x - r - 4, y, x + r + 4, y], fill="red", width=2)
                d.line([x, y - r - 4, x, y + r + 4], fill="red", width=2)
                return img

            mark(before).save(os.path.join(snapshots_dir, f"step_{idx:04d}_before.png"))
            mark(after).save(os.path.join(snapshots_dir, f"step_{idx:04d}_after.png"))

            region = step.get("region")
            if region:
                region_img = self._perception.capture_region(
                    region["left"], region["top"], region["width"], region["height"],
                )
                region_img.save(os.path.join(screenshots_dir, f"step_{idx:04d}.png"), "PNG")

            logger.info("step %d: clicked (%d, %d), snapshots saved", idx, x, y)

        logger.info(
            "pipeline complete: %d steps executed, run dir: %s",
            len(steps), run_dir,
        )