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
| Ctrl+S | 保存工作流 |
| F5 | 回放最新的工作流 |

> 框选状态下（第一次 F3 之后），按 F2 可在框内指定精确点击位置；按 ESC 则使用框中心作为默认点击点。

## 回放

```bash
uv run python main.py run <workflow.json>
```

回放时，`replay.start_delay_seconds`（默认 0 秒，可在 `config/system.yaml` 中调整）控制执行第一个步骤前的等待时间，让你有充足时间切换到目标窗口。

截图和快照仅在回放时生成——录制只输出 JSON。

## 目录结构

```text
data/
  recordings/{会话}-{N}steps/
    {运行时间戳}/
      screenshots/               # 区域截图（回放时重新截取）
      snapshots/                 # 红叉证据（before + after）
  workflows/{会话}-{N}steps.json  # 工作流 JSON
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
- Windows 下需要管理员权限（keyboard 库限制）
