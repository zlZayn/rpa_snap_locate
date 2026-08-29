# engine/ — 规则层

继承根规则，见 [../AGENTS.md](../AGENTS.md)。

engine/ 特有约束：
- 鼠标钩子回调必须轻量：先取时间再处理，不截图、不弹窗、不写文件
- 工作流保存和回放前必须调用 `validate_timeline_events()`，不合法事件不写成有效文件
- 时间线调度使用绝对截止时间 `deadline = origin + offset_ns`，不把上一步耗时加进下一步等待
- `TimelineScheduler` 的 `finally` 必须尝试释放所有仍按下按钮，降低鼠标卡住风险
- 不写"有什么文件/怎么改"，那是 [README.md](README.md) 的职责
