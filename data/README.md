# data/ — 工作流持久化

- 职责：两种工作流 JSON 的保存与读取，回放产物目录管理
- 工作流格式 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 8 节
- 回放产物结构 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 13 节

## 文件索引

| 文件 | 职责 | 关键导出 | 被谁依赖 |
| :--- | :--- | :--- | :--- |
| `data_manager.py` | 时间线/逐步点击工作流的保存与读取 | `DataManager` | main.py、engine/recorder_engine |

## 运行时目录（被 .gitignore 忽略）

| 目录 | 内容 |
| :--- | :--- |
| `workflows/` | 已保存的工作流 JSON 文件 |
| `recordings/` | 每次回放的产物（整段快照、逐事件快照、区域截图、回放报告） |

## 改后必测

- `uv run pytest -q tests/test_data_manager.py`

## 变更影响路由

- 工作流格式变化 → 同步 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 8 节 + [engine/workflow_validator.py](../engine/workflow_validator.py)
- 回放产物结构变化 → 同步 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 13 节
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
