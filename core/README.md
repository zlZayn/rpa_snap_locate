# core/ — 系统能力层

- 职责：屏幕/鼠标感知、坐标定位、Windows 输入注入
- 定位模型说明 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 9 节
- Windows 输入执行 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 12 节

## 文件索引

| 文件 | 职责 | 关键导出 | 被谁依赖 |
| :--- | :--- | :--- | :--- |
| `perception_provider.py` | 截屏、鼠标位置、活动窗口、DPI 与分辨率 | `PerceptionProvider` | engine/、core/action_executor |
| `action_executor.py` | 前台窗口准备、鼠标移动、SendInput 注入 | `ActionExecutor` | engine/timeline_scheduler、engine/pipeline_runner |
| `locator_protocol.py` | 定位接口抽象与工厂 | `BaseLocator`、`create_locator()` | engine/pipeline_runner、core/locators/ |
| `change_validator.py` | 界面变化检测（预留，未实现） | `ChangeValidator` | — |

## 子目录

- [locators/](locators/) — 定位器实现，当前仅 `fixed`

## 改后必测

- `uv run pytest -q tests/test_action_executor.py`
- 手动验证一次完整回放（含多分辨率/DPI 切换）

## 变更影响路由

- 改这里 → 同步 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 9/12 节
- 新增定位器 → 同步 [locators/README.md](locators/README.md)
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
