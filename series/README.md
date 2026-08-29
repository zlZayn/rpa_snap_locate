# series/ — Command Series 编排

- 职责：PowerShell 脚本组合软件启动、等待、鼠标回放、键盘操作和普通命令
- 完整规范 → [docs/COMMAND_SERIES.md](../docs/COMMAND_SERIES.md)
- 原子脚本 → [atoms/](atoms/)

## 文件索引

| 文件 | 职责 |
| :--- | :--- |
| `mouse-keyboard.example.ps1` | 鼠标+键盘组合的完整 Series 示例 |

## 子目录

- [atoms/](atoms/) — 8 个可独立验证的原子脚本
- `mine/` — 用户自定义 Series（被 `.gitignore` 忽略，由 Agent 按需生成）

## 执行方式

```powershell
pwsh -NoProfile -File series/mine/<series-name>.ps1
```

## 变更影响路由

- 新增原子 → 同步 [atoms/README.md](atoms/README.md) + [docs/COMMAND_SERIES.md](../docs/COMMAND_SERIES.md) 第 4 节
- 编排规则变化 → 同步 [docs/COMMAND_SERIES.md](../docs/COMMAND_SERIES.md)
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
