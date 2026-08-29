# data/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

data/ 特有约束：
- `recordings/` 和 `workflows/` 是运行时数据目录，已被 `.gitignore` 忽略，不建双件、不属文档网络
- 工作流 JSON 格式变更必须同步更新 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 8 节和 [engine/workflow_validator.py](../engine/workflow_validator.py)
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
