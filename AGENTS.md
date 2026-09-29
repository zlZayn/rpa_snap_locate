# rpa-snap-locate — 维护索引

## 全局规则
- 架构设计 → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Command Series 规范 → [docs/COMMAND_SERIES.md](docs/COMMAND_SERIES.md)
- 模块手册 → [engine/README.md](engine/README.md) · [core/README.md](core/README.md) · [config/README.md](config/README.md) · [data/README.md](data/README.md) · [series/README.md](series/README.md) · [utils/README.md](utils/README.md) · [tests/README.md](tests/README.md)
- 决策记录 → [.agents/notes/](.agents/notes/)
- 双件分离：AGENTS.md 只写规则，README.md 只写是什么/怎么改

## 常用命令

- 本地钩子：`pre-commit install`（每个 clone 一次；本体 `uv tool install pre-commit`）——提交前自动 `ruff check --fix` + `ruff format`；CI（windows-latest）只读跑同一组检查
- 安装依赖：`uv sync`
- 录制：`uv run python main.py`
- 回放指定文件：`uv run python main.py run data/workflows/<file>.json`
- 测试：`uv run pytest -q`
- Lint：`uv run ruff check .`（ruff 默认规则集，列宽默认 88）
- 格式化：`uv run ruff format .`（`--check` 只看不改）
- 必须从项目根目录执行（config 中路径为相对路径）

## 验证快照（2026-09-27 实测）
- pytest: 51 passed / 0 failed（`uv run pytest -q --basetemp=".pytest_tmp"`，系统 Temp 目录权限受限需指定项目内临时目录）
- Ruff: `check` 0 发现；`format --check` 全绿（全量格式化已落地）

## 待办
- [ ] 无

## 活跃坑
- Windows UIPI：回放进程与目标软件必须同权限级别，否则 SendInput 被拒
- 从非项目根目录执行会导致 data/ 和 logs/ 散落

## 文档地图
- 用户文档 → [README.md](README.md) · [README_zh.md](README_zh.md)
- 架构设计 → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Series 串联规范 → [docs/COMMAND_SERIES.md](docs/COMMAND_SERIES.md)
