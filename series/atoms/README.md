# atoms/ — 原子脚本

- 职责：可独立验证的单动作 PowerShell 脚本，供 Command Series 组合调用
- 完整使用规范 → [docs/COMMAND_SERIES.md](../../docs/COMMAND_SERIES.md) 第 4 节

## 原子索引

| 原子 | 用途 | 关键参数 |
| :--- | :--- | :--- |
| `start-app.ps1` | 后台启动 GUI 应用 | `-FilePath`、`-ArgumentList`、`-Maximized` |
| `wait.ps1` | 固定等待 | `-Seconds` |
| `wait-stable.ps1` | 等待稳定（截屏对比或目录文件对比） | `-Mode`、`-PollSeconds`、`-TimeoutSeconds`、`-StableCount` |
| `run-rpa.ps1` | 同步回放鼠标工作流 | `-Workflow` |
| `run-command.ps1` | 同步执行普通 CLI 命令 | `-Name`、`-FilePath`、`-ArgumentList` |
| `send-keys.ps1` | 输入文字或发送快捷键 | `-WindowTitle`/`-CurrentWindow`、`-Text`/`-Keys` |
| `paste.ps1` | 剪贴板粘贴文本（支持 Unicode） | `-WindowTitle`/`-CurrentWindow`、`-Text`、`-ShiftControlV` |
| `eval-browser.ps1` | 通过 Chrome DevTools Protocol 注入 JavaScript | `-Script`、`-Port`、`-TimeoutSeconds` |

## 改后必测

- 用 `pwsh -NoProfile -File` 单独执行修改的原子，验证成功和失败路径
- 手动验证至少一个组合 Series 能正常运行

## 变更影响路由

- 新增原子 → 同步 [docs/COMMAND_SERIES.md](../../docs/COMMAND_SERIES.md) 第 4 节 + [../README.md](../README.md)
- 修改原子参数 → 同步 [docs/COMMAND_SERIES.md](../../docs/COMMAND_SERIES.md) 对应章节
- 使用约束与工作偏好 → 见 [AGENTS.md](AGENTS.md)
