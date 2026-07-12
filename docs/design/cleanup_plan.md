# 清理与补强计划

本文档基于 2026-07-12 的讨论，记录三项已确认的清理与补强工作。每项均包含背景、确认结论、改动清单和注意事项。

## 背景

项目存在三处"写了但没真正生效"的配置或行为，以及一处可补强的用户提示。经讨论确认处理方向后，形成本计划。

## 1. 删除 timing_mode 和 evidence_mode

### 背景

这两个配置写在 [system.yaml](../../config/system.yaml) 中，但代码从未读取和使用。

- `timing_mode` 原本打算做"严格调度 / 宽松调度"切换：严格模式照原定时间执行每一步，宽松模式在某步慢了时整体推迟后续步骤。只有严格模式实现了，宽松从未做。
- `evidence_mode` 原本打算做"整段前后截图 / 逐事件截图"切换。实际确认后发现：burst 和 per-event 两种截图现在同时存在（每次回放既产出 burst_before/after，也产出每个事件的 before/after），根本不需要切换开关。

### 确认结论

删除。两种截图模式同时存在，evidence_mode 没有存在理由；宽松调度从未实现，timing_mode 也是空壳。

### 改动清单

**配置文件**：
- [system.yaml](../../config/system.yaml) 第 18 行 `timing_mode: strict` 删除
- [system.yaml](../../config/system.yaml) 第 20 行 `evidence_mode: burst` 删除

**文档**：
- [ARCHITECTURE.md](../ARCHITECTURE.md) 第 446 行 `replay.timing_mode` 配置表行删除
- [ARCHITECTURE.md](../ARCHITECTURE.md) 第 447 行 `replay.evidence_mode` 配置表行删除
- [ARCHITECTURE.md](../ARCHITECTURE.md) 第 483 行已知限制中"timing_mode、evidence_mode 和框选超时配置尚未形成可切换行为"这一条更新为仅剩框选超时相关表述，或整体删除
- [evolution_notes.md](./evolution_notes.md) 第 61 行更新措辞
- [evolution_notes.md](./evolution_notes.md) 第 115 行更新措辞
- [evolution_notes.md](./evolution_notes.md) 第 236 行待讨论问题删除或标记为已决定

**代码**：无改动。代码本来就没读这两个配置。

### 注意事项

无。零代码改动，不影响任何运行行为。

## 2. 删除 box_select_timeout_seconds

### 背景

[system.yaml](../../config/system.yaml) 中配置了 `box_select_timeout_seconds: 10`，[recorder_engine.py](../../engine/recorder_engine.py) 第 41-43 行读取了这个值存到 `self._timeout_seconds`，但之后从未使用。也就是说：用户按了第一次 F3 开始框选后，即使过了 10 秒没按第二次 F3，框选状态也不会自动取消。

### 确认结论

删干净。框选操作通常很快，用户可以手动按 ESC 取消，不需要自动超时。删掉配置和读取逻辑，避免误导。

### 改动清单

**配置文件**：
- [system.yaml](../../config/system.yaml) 第 13 行 `box_select_timeout_seconds: 10` 删除

**代码**：
- [recorder_engine.py](../../engine/recorder_engine.py) 第 41-43 行删除 `self._timeout_seconds = self._config.get(...)` 整块

**文档**：
- [ARCHITECTURE.md](../ARCHITECTURE.md) 第 443 行 `recorder.box_select_timeout_seconds` 配置表行删除
- [evolution_notes.md](./evolution_notes.md) 第 61 行更新措辞
- [evolution_notes.md](./evolution_notes.md) 第 115 行更新措辞
- [evolution_notes.md](./evolution_notes.md) 第 237 行待讨论问题删除或标记为已决定

### 注意事项

- `self._cancel_event`（第 40 行）是独立逻辑，用于 ESC 取消框选，不受本次删除影响，保留不动。
- 测试中 mock 了 `_cancel_event` 但未涉及 `_timeout_seconds`，删除后不影响现有测试。

## 3. 加强异常补发抬起的终端提示

### 背景

[timeline_scheduler.py](../../engine/timeline_scheduler.py) 第 109-119 行有 finally 块：回放在鼠标按下后、抬起前异常中断时，尝试补发抬起信号，避免鼠标卡在按住状态。补发成功用 `logger.warning`，失败用 `logger.exception`。

现有测试 [test_timeline_scheduler.py](../../tests/test_timeline_scheduler.py) 第 70-96 行已覆盖中断场景，验证补发被调用。

问题：日志只在日志系统里，如果用户不看日志，不会知道发生过异常补发。

### 确认结论

加强终端提示。在现有 logger 之外，加一行直接打印到终端的提示，让不看日志的用户也能注意到。

### 改动清单

**代码**：
- [timeline_scheduler.py](../../engine/timeline_scheduler.py) 第 109-119 行：在 `logger.warning` 和 `logger.exception` 之外，各加一行 `print` 直接输出到终端。内容应明确告知"回放中断，已自动释放鼠标按键"或"回放中断，释放鼠标按键失败，请手动点击"。

**文档**：
- [ARCHITECTURE.md](../ARCHITECTURE.md) 第 329 行：更新描述，说明补发时会同时在终端打印提示
- [evolution_notes.md](./evolution_notes.md) 第 119 行更新措辞
- [evolution_notes.md](./evolution_notes.md) 第 223 行标记为已决定
- [evolution_notes.md](./evolution_notes.md) 第 238 行标记为已决定

### 注意事项

- 只加 `print`，不改现有 `logger` 调用，保持日志系统记录完整。
- 不改测试。现有测试验证补发行为被调用，不涉及终端输出检查。

## 执行顺序

建议按以下顺序执行，每步完成后可单独验证：

1. 删 timing_mode 和 evidence_mode（纯配置和文档，零代码风险）
2. 删 box_select_timeout_seconds（配置 + 一处代码，`_cancel_event` 不受影响）
3. 加强异常补发终端提示（一处代码 + 文档）

## 验证方式

- 第 1 步：改完后 `uv run python main.py` 启动录制，确认程序正常启动、F2/F3/Ctrl+S/F5 全部正常工作。
- 第 2 步：同上，额外确认 F3 框选仍可正常使用、ESC 仍可取消框选。
- 第 3 步：构造一个会中断的回放场景（或直接看代码逻辑），确认终端有提示输出。日常使用中此项不易触发，主要靠代码审查确认。
- 全部完成后运行测试：`uv run python -m pytest tests/`，确认无回归。
