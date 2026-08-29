# tests/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

tests/ 特有约束：
- 单元测试使用 fake clock 和 mock，不真实移动鼠标
- 测试文件名与被测模块对应：`test_<module>.py`
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
