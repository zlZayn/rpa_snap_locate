# RPA Snap Locate

纯视觉驱动的桌面自动化录制和回放工具。固定坐标 + 截图区域定位，预留 LLM 插槽。

## 快速开始

```bash
uv sync
uv run python main.py             # 录制模式（热键驱动）
uv run python main.py run <workflow.json>  # 回放模式
```

## 热键（录制模式）

| 热键 | 功能 |
| :--- | :--- |
| F2 | 在鼠标位置记录一个点击步骤 |
| F3 | 两次按压框选区域 |
| ESC | 取消当前框选 / 使用框中心 |
| Ctrl+S | 保存工作流 |
| F5 | 回放最新的工作流 |

## 目录结构

```
data/
  recordings/{会话}-{N}steps/
    {运行时间戳}/
      screenshots/               # 区域截图（回放时重新截取）
      snapshots/                 # 红叉证据（before + after）
  workflows/{会话}-{N}steps.json  # 工作流 JSON
```

录制只写 JSON，截图和快照全部在回放时生成。每次回放自包含一个 `{运行时间戳}` 目录。

## 管理权限

Windows 下需要管理员权限运行（keyboard 库限制）。