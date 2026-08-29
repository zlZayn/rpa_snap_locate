# config/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

config/ 特有约束：
- `system.yaml` 中 `paths.*` 必须为相对路径，工具须从项目根目录执行
- 新增配置项必须同步更新 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 第 16 节"配置项及真实生效状态"
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
