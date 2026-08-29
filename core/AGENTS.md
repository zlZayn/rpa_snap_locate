# core/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

core/ 特有约束：
- 所有 Win32 API 返回值必须检查；`SendInput` 被拒时抛出含 UIPI 说明的 `PermissionError`，不记录虚假成功
- 新定位器必须继承 `BaseLocator` 并在 `create_locator()` 工厂中注册
- 输入采集回调必须轻量，不截图、不弹窗、不写文件
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
