# engine/ — 流程编排层

- 职责：录制状态机、事件采集、工作流校验、时间调度、回放编排
- 录制状态机 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 6 节
- 回放链路 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 10 节
- 绝对时间调度 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 11 节

## 文件索引

| 文件 | 职责 | 关键导出 | 被谁依赖 |
| :--- | :--- | :--- | :--- |
| `recorder_engine.py` | 时间线/逐步点击两套录制状态机 | `RecorderEngine`、`RecorderState` | main.py |
| `input_event_recorder.py` | 鼠标钩子、单调时间戳、线程安全队列、事件转换 | `InputEventRecorder`、`InputRecordingError` | recorder_engine |
| `workflow_validator.py` | 时间线结构、顺序、按下/抬起配对校验 | `validate_timeline_events()`、`ValidationError` | data_manager、pipeline_runner |
| `timeline_scheduler.py` | 绝对截止时间调度、迟到统计、安全释放 | `TimelineScheduler` | pipeline_runner |
| `pipeline_runner.py` | 两种工作流分发、定位、执行、回放产物 | `PipelineRunner` | main.py |
| `hotkey_registry.py` | keyboard 全局热键封装 | `HotkeyRegistry` | main.py |
| `step_builder.py` | 逐步点击模式构造 click 步骤 | `StepBuilder` | recorder_engine |

## 改后必测

- `uv run pytest -q tests/`（全部引擎测试）
- 手动验证：F2 录制 → Ctrl+S 保存 → F5 回放完整流程

## 变更影响路由

- 改这里 → 同步 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 6/10/11 节
- 工作流格式变化 → 同步 [data/README.md](../data/README.md) + [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 8 节
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
