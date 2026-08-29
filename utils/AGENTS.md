# utils/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

utils/ 特有约束：
- 工具模块必须无状态、可独立测试，不依赖 engine/ 或 core/ 的运行时状态
- 预留模块（hash_calculator、image_entropy_calculator）保持空壳，不擅自实现
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
