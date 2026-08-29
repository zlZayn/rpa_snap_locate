# locators/ — 定位器实现

- 职责：将工作流中的归一化坐标还原为当前物理坐标
- 定位模型 → [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) 第 9 节
- 接口与工厂 → [../locator_protocol.py](../locator_protocol.py)

## 文件索引

| 文件 | 职责 | 关键导出 | 被谁依赖 |
| :--- | :--- | :--- | :--- |
| `fixed_locator.py` | 归一化坐标转当前物理坐标（DPI + 分辨率感知） | `FixedLocator` | `create_locator()` 工厂 |

## 当前支持

- `method: "fixed"` — 唯一已实现的定位方式
- `llm` 等视觉定位不属本项目内核，由 Command Series 调用外部工具处理

## 改后必测

- `uv run pytest -q`（定位相关测试）

## 变更影响路由

- 新增定位器 → 同步 [../locator_protocol.py](../locator_protocol.py) 工厂 + [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) 第 9 节
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
