# RPA Snap Locate

[English](README.md) | [简体中文](README_zh.md)

纯视觉驱动的桌面自动化录制和回放工具。固定坐标 + 截图区域定位，预留 LLM 插槽。

## 快速开始

```bash
uv sync
uv run python main.py                        # 录制模式（热键驱动）
uv run python main.py run data/workflows/<file>.json  # 回放模式
```

## 热键（录制模式）

| 热键 | 功能 |
| :--- | :--- |
| F2 | 在鼠标位置记录一个点击步骤 |
| F3 | 两次按压框选区域 |
| ESC | 取消当前框选 |
| Ctrl+S | 保存当前工作流并开始新录制 |
| F5 | 回放最新的工作流 |

> 框选状态下（第一次 F3 之后），按 F2 可在框内指定精确点击位置；按 ESC 则使用框中心作为默认点击点。

每次保存只包含程序启动后或上次保存后录制的步骤。保存成功后，步骤编号和未完成的框选状态都会重置，可立即开始新的工作流。没有已录制步骤时按 Ctrl+S 不会执行任何操作。

## 回放

```bash
uv run python main.py run <workflow.json>
```

回放时，`replay.start_delay_seconds`（默认 0 秒，可在 `config/system.yaml` 中调整）控制执行第一个步骤前的等待时间，让你有充足时间切换到目标窗口。

截图和快照仅在回放时生成——录制只输出 JSON。

Windows 下，回放进程与目标软件必须处于相同权限级别。Windows 会拦截普通进程向管理员窗口注入的模拟输入。建议两者都以普通权限运行；如果目标软件必须以管理员身份运行，回放进程也必须提升到相同权限。点击被拒绝时程序会明确报错，不会再记录成虚假的成功。

## 串联脚本

将软件启动和 RPA 回放串联成一个脚本，方便 AI 代理直接生成和执行。参见 [`examples/series.template.ps1`](examples/series.template.ps1)（PowerShell）、[`examples/series.template.sh`](examples/series.template.sh)（Bash）和 [`docs/COMMAND_SERIES.md`](docs/COMMAND_SERIES.md)。

Windows 下应优先直接启动软件的 GUI `.exe`。`.cmd` 或 `.bat` 启动器可能在软件整个生命周期内保留控制台宿主；必须使用此类启动器时，PowerShell 模板会隐藏该宿主窗口。

## 目录结构

```text
data/
  recordings/[{名称}-]{时间戳}-{N}steps/
    {运行时间戳}/
      screenshots/               # 区域截图（回放时重新截取）
      snapshots/                 # 红叉证据（before + after）
  workflows/[{名称}-]{时间戳}-{N}steps.json  # 工作流 JSON；名称可选
```

## 配置说明

编辑 `config/system.yaml`：

| 配置段 | 键 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `screen` | `logical_width`, `logical_height` | 1920, 1080 | 逻辑分辨率 |
| `screen` | `dpi_scale` | auto | DPI 缩放比 |
| `replay` | `start_delay_seconds` | 0 | 首个步骤执行前的等待秒数 |

## 依赖要求

- Python >= 3.11
- uv（包管理器）
- Windows 录制模式的全局热键可能需要管理员权限
- 回放进程与目标软件必须使用相同的 Windows 权限级别
