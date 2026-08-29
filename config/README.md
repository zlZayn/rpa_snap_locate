# config/ — 配置管理

- 职责：YAML 单例配置读取，提供屏幕、路径、录制与回放参数
- 配置文件 → [system.yaml](system.yaml)
- 完整配置说明 → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 16 节

## 文件索引

| 文件 | 职责 | 关键导出 | 被谁依赖 |
| :--- | :--- | :--- | :--- |
| `config_manager.py` | YAML 单例加载与层级取值 | `ConfigManager` | main.py、engine/、core/、utils/ |
| `system.yaml` | 屏幕/DPI、路径、录制、回放参数 | — | ConfigManager.load() |

## 改后必测

- `uv run pytest -q`（配置加载相关测试）
- 手动验证 `uv run python main.py` 能正常读取配置

## 变更影响路由

- 改这里 → 同步根 [AGENTS.md](../AGENTS.md) 活跃坑（如路径规则变化）
- 新增配置项 → 同步 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 16 节
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
