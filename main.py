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

    def show_help():
        logger.info("-" * 54)
        if recorder.is_timeline_mode:
            logger.info("主流程：F2 开始 → 操作鼠标 → Ctrl+S 保存 → F5 回放")
            logger.info("  Ctrl+Delete 清空尚未保存的操作记录")
            logger.info("  Ctrl+S      保存（如正在录制则先停止再保存）")
            logger.info("  ESC         取消进行中的框选")
            logger.info("  F1          显示本帮助")
            logger.info("  F2          开始录制；再次按下停止并保留，可继续追加")
            logger.info("  F3          框选截图范围：按两次 F3 标记矩形区域，回放后自动截图保存；不改变点击定位方式")
            logger.info("  F5          回放最近保存的文件")
        else:
            logger.info("主流程：鼠标移到目标 → F2 记一次点击 → Ctrl+S 保存 → F5 回放")
            logger.info("  Ctrl+Delete 清空尚未保存的操作记录")
            logger.info("  Ctrl+S      保存当前工作流")
            logger.info("  ESC         取消进行中的框选")
            logger.info("  F1          显示本帮助")
            logger.info("  F2          在鼠标位置记录一次点击")
            logger.info("  F3          框选范围：按两次 F3 标记矩形区域，随后按 F2 记录框内相对位置")
            logger.info("  F5          回放最近保存的文件")
        logger.info("-" * 54)

    def on_run():
        if recorder.has_unsaved_actions:
            logger.warning(
                "【回放】当前还有未保存内容。请先按 Ctrl+S 保存，"
                "或按 Ctrl+Delete 清空；本次没有启动回放。"
            )
            return
        config = ConfigManager()
        wf = config.get("paths", "workflows_dir")
        files = glob.glob(os.path.join(wf, "*.json"))
        if not files:
            logger.warning("【回放】还没有保存过录制。先按 F2 开始，再按 Ctrl+S 保存。")
            return
        wp = max(files, key=os.path.getmtime)
        logger.info("【回放】开始执行：%s", wp)

        def _run():
            try:
                runner.run(wp)
                logger.info("【回放】执行完成")
            except Exception as e:
                logger.exception("【回放】执行失败：%s", e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def on_f2():
        continuing = recorder.recorded_action_count > 0
        msg = recorder.on_f2()
        if msg == "recording started":
            if continuing:
                logger.info("【录制】已继续。按 Ctrl+S 保存，或按 F2 停止。")
            else:
                logger.info("【录制】已开始。按 F2 停止，或完成操作后按 Ctrl+S 保存。")
        elif msg == "recording stopped":
            logger.info(
                "【录制】已停止，当前已记录 %d 次操作。按 Ctrl+S 保存，"
                "或按 F2 继续追加。",
                recorder.recorded_action_count,
            )
        elif msg.startswith("recording failed"):
            logger.error(
                "【录制】停止时发现事件不完整（可能是录制过程中鼠标按键未松开）。"
                "按 Ctrl+Delete 清空后重新录制。"
            )
        elif recorder.is_timeline_mode:
            logger.info("【录制】%s", msg)
        else:
            logger.info(
                "【录制】已记录第 %d 次点击。继续移动鼠标并按 F2，"
                "完成后按 Ctrl+S 保存。",
                recorder.recorded_action_count,
            )

    def on_f3():
        msg = recorder.on_f3()
        if msg.startswith("first corner recorded"):
            logger.info("【框选】已记住第一个角。移到对角后再按一次 F3。")
        elif msg.startswith("box selection complete"):
            if recorder.is_timeline_mode:
                logger.info("【框选】区域已确定，已加入截图列表。继续操作鼠标即可。")
            else:
                logger.info("【框选】区域已确定。把鼠标移到目标后按 F2。")
        else:
            logger.warning("【框选】只能在录制过程中使用。请先按 F2 开始录制。")

    def on_cancel():
        msg = recorder.on_cancel()
        if msg == "box selection cancelled":
            logger.info("【框选】已取消，录制继续。")
        else:
            logger.info("【框选】当前没有需要取消的框选。")

    def on_save():
        msg = recorder.save()
        if msg.startswith("saved "):
            logger.info("【保存】成功：%s", recorder.last_saved_path)
            logger.info("【下一步】按 F5 回放；要录新内容，再按 F2。")
        elif msg in {"no events to save", "no steps to save"}:
            logger.warning("【保存】没有可保存的操作。请先按 F2 开始录制。")
        elif "without matching mouse_up" in msg:
            logger.error(
                "【保存】失败：录制结束时鼠标按键仍处于按下状态（可能是录制过程中"
                "按下了未松开）。按 Ctrl+Delete 清空后重新录制。"
            )
        else:
            logger.error("【保存】失败：%s", msg.removeprefix("save failed: "))

    def on_clear():
        msg = recorder.clear()
        logger.info("【清空】尚未保存的内容已清除。按 F2 可重新开始。")

    def on_help():
        show_help()

    registry.register("F2", on_f2)
    registry.register("F3", on_f3)
    registry.register("esc", on_cancel)
    registry.register("ctrl+s", on_save)
    registry.register("F5", on_run)
    registry.register("F1", on_help)
    registry.register("ctrl+delete", on_clear)

    mode = "完整时间录制" if recorder.is_timeline_mode else "单步点击录制"
    logger.info("RPA 鼠标录制器已就绪（%s）", mode)
    show_help()

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
