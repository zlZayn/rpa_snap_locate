# series/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

series/ 特有约束：
- 必须用 `pwsh`（7+）执行，不能用 `powershell`（5.1）；始终加 `-NoProfile`
- `mine/` 是用户自定义 Series 目录，已被 `.gitignore` 忽略，不建双件、不属文档网络
- 原子失败后立即停止 Series，不忽略非零退出码
- RPA、键盘原子和目标软件必须用同一个 Windows 权限级别运行
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
