# tests/ — 测试套件

- 职责：核心模块单元测试，使用 fake clock 和 mock，不真实移动鼠标
- 运行方式：`uv run pytest -q`

## 测试对应关系

| 测试文件 | 被测模块 | 覆盖要点 |
| :--- | :--- | :--- |
| `test_recorder_engine.py` | `engine/recorder_engine.py` | 录制状态机、分段合并、逐步点击模式 |
| `test_input_event_recorder.py` | `engine/input_event_recorder.py` | 鼠标钩子、单调时间戳、队列、事件转换 |
| `test_workflow_validator.py` | `engine/workflow_validator.py` | 时间线结构、顺序、按下/抬起配对校验 |
| `test_timeline_scheduler.py` | `engine/timeline_scheduler.py` | 绝对截止时间调度、迟到统计、安全释放 |
| `test_pipeline_runner.py` | `engine/pipeline_runner.py` | 两种工作流分发、定位、执行、回放产物 |
| `test_action_executor.py` | `core/action_executor.py` | Windows 输入注入、前台窗口准备 |
| `test_data_manager.py` | `data/data_manager.py` | 工作流保存与读取 |

## 特殊坑

- 真实 Windows 双击识别、不同权限窗口和高负载下的时间误差需手工或专用桌面集成测试
- 涉及 Windows API 的测试需 mock，不能在 CI 中真实注入鼠标事件

## 变更影响路由

- 新增模块 → 同步新增对应 `test_<module>.py`
- 修改模块行为 → 同步更新对应测试
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
