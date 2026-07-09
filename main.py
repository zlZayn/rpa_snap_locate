import sys
import os
import glob
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config_manager import ConfigManager
from engine.hotkey_registry import HotkeyRegistry
from engine.recorder_engine import RecorderEngine
from engine.pipeline_runner import PipelineRunner
from utils.logger_setup import setup_logger


def cmd_record():
    config = ConfigManager()
    config.load()

    logger = setup_logger(
        name="rpa_snap_locate",
        log_dir=config.get("paths", "logs_dir", default="logs"),
    )

    recorder = RecorderEngine()
    registry = HotkeyRegistry()
    runner = PipelineRunner()

    def on_run():
        config = ConfigManager()
        wf = config.get("paths", "workflows_dir")
        files = sorted(glob.glob(os.path.join(wf, "*.json")))
        if not files:
            logger.warning("[RUN] no workflows found in %s", wf)
            return
        wp = files[-1]
        logger.info("[RUN] replaying %s ...", wp)

        def _run():
            try:
                runner.run(wp)
            except Exception as e:
                logger.exception("[RUN] replay failed: %s", e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def on_f2():
        msg = recorder.on_f2()
        logger.info("[F2] %s", msg)

    def on_f3():
        msg = recorder.on_f3()
        logger.info("[F3] %s", msg)

    def on_cancel():
        msg = recorder.on_cancel()
        if msg:
            logger.info("[ESC] %s", msg)

    def on_save():
        msg = recorder.save()
        logger.info("[SAVE] %s", msg)

    def on_clear():
        msg = recorder.clear()
        logger.info("[CLEAR] %s", msg)

    registry.register("F2", on_f2)
    registry.register("F3", on_f3)
    registry.register("esc", on_cancel)
    registry.register("ctrl+s", on_save)
    registry.register("F5", on_run)

    logger.info("=" * 50)
    logger.info("Visual RPA Recorder started")
    logger.info("  F2      - record click at mouse position")
    logger.info("  F3      - start/end box selection (2 presses)")
    logger.info("  ESC     - cancel current box selection")
    logger.info("  Ctrl+S   - save workflow to file")
    logger.info("  F5      - replay saved workflow")
    logger.info("=" * 50)

    registry.start_listening()


def cmd_run(workflow_path: str):
    config = ConfigManager()
    config.load()
    logger = setup_logger(
        name="rpa_snap_locate",
        log_dir=config.get("paths", "logs_dir", default="logs"),
    )
    runner = PipelineRunner()
    runner.run(workflow_path)


def main():
    args = sys.argv[1:]

    if not args:
        cmd_record()
    elif args[0] == "run":
        if len(args) < 2:
            print("usage: uv run python main.py run <workflow.json>")
            sys.exit(1)
        cmd_run(args[1])
    else:
        print("usage: uv run python main.py          (record mode)")
        print("       uv run python main.py run <file>  (replay mode)")
        sys.exit(1)


if __name__ == "__main__":
    main()