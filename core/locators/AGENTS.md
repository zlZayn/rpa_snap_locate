# locators/ — 规则层

继承根规则，见 [../../AGENTS.md](../../AGENTS.md)。

locators/ 特有约束：
- 新定位器必须继承 `BaseLocator`（定义于 [../locator_protocol.py](../locator_protocol.py)）并在 `create_locator()` 注册
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
