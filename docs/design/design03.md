# 截图作为时间线一等事件

**状态**：计划中，未实现
**目标版本**：5.1

## 动机

当前 `capture_regions` 是工作流 JSON 顶层的一个独立数组，回放结束后统一截图。这种做法有两个问题：

1. 截图和点击是脱节的——不知道某个区域在时间线的哪个节点被截取
2. 无法在两次点击之间截图，比如“点开菜单后先截图，再点菜单项”

## 设计

### 录制阶段

F3 框选两个角后，不再追加到 `_capture_regions`，而是在时间线中插入一条 `screenshot` event。该 event 的 `offset_ns` 是第二次 F3 按下时相对首个输入事件的时间。

```python
{
    "index": N,
    "type": "screenshot",
    "region": {"left": 100, "top": 200, "width": 400, "height": 400},
    "offset_ns": 12345678900,
    "window_title": "记事本"
}
```

F3 可以在录制中的任何时刻按，截图 event 的 `offset_ns` 由 `InputEventRecorder` 的时间线确定。Index 与 mouse_down/mouse_up 共享递增序列。

### 工作流 JSON 变化

顶层不再有 `capture_regions` 字段。screenshot 和 mouse_down/mouse_up 平级，都在 `events` 数组里，按 `(offset_ns, index)` 排序：

```json
{
    "version": "5.1",
    "events": [
        {"index": 1, "type": "screenshot", "region": {...}, "offset_ns": 0},
        {"index": 2, "type": "mouse_down", ...},
        {"index": 3, "type": "mouse_up", ...},
        {"index": 4, "type": "screenshot", "region": {...}, "offset_ns": 250000000},
    ]
}
```

### 回放阶段

`TimelineScheduler` 需要处理 type `screenshot`：

- `prepare_down` 阶段：无事可做（截图不需要窗口激活或鼠标移动）
- `mouse_down` 回调：改为 `capture_region`，截取区域图保存到 `screenshots/`

截图时机：按照自己的 deadline 执行，与 mouse event 同等调度。截图耗时可能影响后续事件的准时性，报告会如实记录为 `preparation_delay` 或 `lateness`。

### 产物变化

`screenshots/` 下的文件名从 `region_N.png` 改为 `event_N.png`，对应 event index。

### 需要修改的文件

| 文件 | 改动 |
|------|------|
| `engine/recorder_engine.py` | `_timeline_f3` 不再追加 `_capture_regions`，改为在 `InputEventRecorder` 的时间线上记录截图事件 |
| `engine/input_event_recorder.py` | 新增 `capture_screenshot(region)` 方法，往队列写入一条 screenshot 类型的 raw_event；`_build_workflow_events` 转换时保留 type、region |
| `engine/workflow_validator.py` | 允许 type `screenshot`，不参与 down/up 配对校验；必须包含 `region` |
| `engine/timeline_scheduler.py` | run() 的 prepare/mouse_down/mouse_up 回调改为通用 callback 接口；screenshot 事件走截图逻辑 |
| `engine/pipeline_runner.py` | `_run_v5` 中不再单独遍历 `capture_regions`，screenshot 在 scheduler 内完成 |
| `data/data_manager.py` | `save_workflow_v5` 不再接受 `capture_regions` 参数 |
| `core/perception_provider.py` | 已有 `capture_region()`，无需新增 |

### 边界情况

- F3 在录制开始前或停止后按下：仍有 `RECORDING_WAITING_SECOND` 状态机保护，拒绝操作
- F3 在没有任何 click 事件的情况下截图：screenshot event 可以有 `offset_ns == 0`（F3 在第一个 click 之前按下），校验器不要求首个 event 是 mouse_down
- F3 在两次 F2 分段录制之间按下：暂停区间不产生事件，截图 timestamp 跨分段时由 `_append_timeline_events` 正确重映射
