# utils/ — 无状态工具

- 职责：DPI 计算、日志设置、哈希与图像熵检测（预留）
- 所有模块无状态，可独立导入和测试

## 文件索引

| 文件 | 职责 | 关键导出 | 被谁依赖 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| `dpi_calculator.py` | 系统 DPI 读取、物理坐标与归一化坐标互转 | `get_system_dpi_scale()`、`phys_to_normalized()`、`normalized_to_phys()` | core/、engine/ | 已实现 |
| `logger_setup.py` | 日志初始化（文件 + 控制台） | `setup_logger()` | main.py | 已实现 |
| `hash_calculator.py` | 图像哈希计算 | `HashCalculator` | — | 预留，未实现 |
| `image_entropy_calculator.py` | 图像熵检测 | `ImageEntropyCalculator` | — | 预留，未实现 |

## 改后必测

- `uv run pytest -q`（如修改影响被依赖模块）

## 变更影响路由

- 实现预留模块 → 同步 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 对应章节
- 修改 dpi_calculator → 同步 [core/README.md](../core/README.md) 定位相关说明
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
