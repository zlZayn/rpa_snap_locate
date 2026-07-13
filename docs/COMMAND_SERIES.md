# Command Series 组装规范

本文档主要供 Agent 设计和生成 Command Series，也可供人工编写时参考。

Command Series 是一个 PowerShell 脚本：它按顺序调用独立原子，组合软件启动、等待、鼠标回放、键盘操作和普通命令。Series 只负责编排，不复制原子的内部实现。

```text
启动软件 → 等待就绪 → 鼠标回放 → 键盘操作 → 后续命令
```

## 1. 能力边界

- 本项目只录制鼠标工作流；
- `run-rpa.ps1` 只回放已经存在的鼠标工作流，不现场录制；
- `send-keys.ps1` 直接输入文字或发送快捷键，不录制键盘；
- 不支持拖拽；
- 视觉模型当前不实现，也没有原子模板。

## 2. Agent 工作流程

Agent 必须按以下顺序工作：

1. 理解用户想做成的实际效果；
2. 调查目标软件是否自带命令行参数或专用 CLI；
3. 用人话向用户解释每一步要干什么；
4. 确认所有不能自己猜的信息；
5. 只读本次需要的原子；
6. 在 `series/mine/` 创建具体 Series；
7. 检查路径、占位符和 PowerShell 语法；
8. 报告用了哪些原子、检查结果和还缺什么。

不能先生成脚本让用户猜脚本会干什么。

## 3. 生成前必须确认

根据任务需要确认以下信息，别问无关的：

| 信息 | 需要确认的内容 |
| :--- | :--- |
| 目标软件 | 软件名称和实际可执行文件路径 |
| 软件能力 | 是否支持通过启动参数打开页面、文件、项目或设置窗口状态 |
| 鼠标回放 | 使用哪些已有工作流，JSON 路径是否真实存在 |
| 键盘文字 | 输入什么内容，发送到哪个窗口 |
| 快捷键 | 发送什么组合键，发送到哪个窗口 |
| 等待 | 哪个步骤需要等待，是否有明确就绪条件 |
| 普通命令 | 命令、参数及成功标准 |
| 执行顺序 | 每一步的先后关系 |

用户不理解术语时，先用实际操作结果解释，再提问。例如不要只问“使用 `-CurrentWindow` 还是 `-WindowTitle`”，应先说明：

- 指定窗口标题：脚本先查找并激活该窗口，但标题变化时可能找不到；
- 使用当前窗口：不查找标题，但必须确定上一步已经把正确窗口置于前台。

## 4. 原子目录

原子在 `series/atoms/`。只读本次会用到的文件。

| 原子 | 用途 | 关键参数 |
| :--- | :--- | :--- |
| [`start-app.ps1`](../series/atoms/start-app.ps1) | 后台启动 GUI | `-FilePath`、`-ArgumentList`、`-Maximized` |
| [`wait.ps1`](../series/atoms/wait.ps1) | 固定等待 | `-Seconds` |
| [`run-rpa.ps1`](../series/atoms/run-rpa.ps1) | 同步回放鼠标工作流 | `-Workflow` |
| [`send-keys.ps1`](../series/atoms/send-keys.ps1) | 输入文字或发送快捷键 | 目标参数加 `-Text` 或 `-Keys` |
| [`paste.ps1`](../series/atoms/paste.ps1) | 剪贴板粘贴文本（支持中文等 Unicode） | `-Text`、`-WindowTitle` / `-CurrentWindow` |
| [`run-command.ps1`](../series/atoms/run-command.ps1) | 同步执行普通 CLI | `-Name`、`-FilePath`、`-ArgumentList` |
| [`wait-stable.ps1`](../series/atoms/wait-stable.ps1) | 等待画面停止变化（纯内存截屏对比） | `-IntervalSecond`、`-Threshold`、`-TimeoutSecond` |

### 4.1 启动软件

```powershell
& (Join-Path $Atoms "start-app.ps1") -FilePath "<APP_EXE>" -Maximized
```

优先使用目标软件自身的命令行能力：

```powershell
& (Join-Path $Atoms "start-app.ps1") `
    -FilePath "<APP_EXE>" `
    -ArgumentList @("<APP_SPECIFIC_ARGUMENT>")
```

`-Maximized` 只是 Windows 层面的尝试，软件可能不认。如果软件自带最大化、打开网址、打开文件或加载项目等参数，直接写在具体 Series 里，别写进通用原子。

### 4.2 等待

```powershell
& (Join-Path $Atoms "wait.ps1") -Seconds 2
```

优先等窗口、进程、文件或端口等明确就绪信号，实在没法检测再用固定等待。

### 4.3 鼠标回放

```powershell
& (Join-Path $Atoms "run-rpa.ps1") `
    -Workflow "data/workflows/<WORKFLOW_JSON>"
```

工作流必须提前录好、真实存在。该原子同步等待回放结束，失败时中断 Series。

简单的 RPA 单击（mouse_down + mouse_up）由 Agent 直接写 workflow JSON 即可，无需用户录制。

浏览器场景尤其有用：先点击页面把焦点切入页面内部，后续键盘操作（Tab、快捷键、粘贴）才不会打在地址栏或标签栏上。

坐标用归一化 0–1，与分辨率无关。格式如下（居中单击）：

```json
{
  "index": 1,
  "type": "mouse_down",
  "button": "left",
  "offset_ns": 0,
  "method": "fixed",
  "norm_x": 0.5,
  "norm_y": 0.5,
  "window_title": "...",
  "dpi_scale": 1.0
},
{
  "index": 2,
  "type": "mouse_up",
  "button": "left",
  "offset_ns": 100000000,
  "position_from_event": 1
}
```

| 字段 | 说明 |
| :--- | :--- |
| `norm_x`/`norm_y` | 0–1 比例坐标，`0.5` 即居中 |
| `offset_ns` | 事件间隔纳秒，mouse_down 到 mouse_up 通常 100ms（`100000000`） |
| `position_from_event` | mouse_up 引用 mouse_down 的坐标，值为 index |

完整 Series 示例在 `series/mine/`（该目录已 gitignore，由 Agent 按需生成）。

### 4.4 键盘输入

向标题稳定的窗口输入文字：

```powershell
& (Join-Path $Atoms "send-keys.ps1") `
    -WindowTitle "<WINDOW_TITLE>" `
    -Text "<TEXT>"
```

向已经确认的当前前台窗口发送快捷键：

```powershell
& (Join-Path $Atoms "send-keys.ps1") `
    -CurrentWindow `
    -Keys "^s"
```

常用 SendKeys 写法：

| 操作 | `-Keys` |
| :--- | :--- |
| Ctrl+S | `^s` |
| Ctrl+Enter | `^{ENTER}` |
| Alt+F4 | `%{F4}` |
| Tab | `{TAB}` |

文字默认逐字符发送。需要降速时用 `-CharacterDelayMilliseconds`。窗口激活耗时可通过 `-AfterActivateMilliseconds` 调整（默认 200ms）。如果输入还是不稳定，优先用软件原生参数或专用 CLI，不要继续堆键盘模拟。

中文等 Unicode 文本不受 SendKeys 支持，应改用 [`paste.ps1`](#46-剪贴板粘贴) 通过剪贴板粘贴。

### 4.5 普通命令

```powershell
& (Join-Path $Atoms "run-command.ps1") `
    -Name "<STEP_NAME>" `
    -FilePath "<CLI>" `
    -ArgumentList @("<ARGUMENT>")
```

这个原子用于跑完就退的前台命令。GUI 或者常驻服务用 `start-app.ps1`。

### 4.6 剪贴板粘贴

向当前前台窗口粘贴文本（支持 Unicode，如中文）：

```powershell
& (Join-Path $Atoms "paste.ps1") `
    -CurrentWindow `
    -Text "你好"
```

向标题稳定的窗口粘贴：

```powershell
& (Join-Path $Atoms "paste.ps1") `
    -WindowTitle "记事本" `
    -Text "你好世界"
```

原理：`Set-Clipboard` 写入文本，再通过 `SendKeys` 发送 `Ctrl+V`。因此对任何支持剪贴板粘贴的控件都有效。

窗口激活耗时可通过 `-AfterActivateMilliseconds` 调整（默认 200ms）。

部分终端使用 `Ctrl+Shift+V` 粘贴，用 `-ShiftControlV` 开关：

```powershell
& (Join-Path $Atoms "paste.ps1") `
    -CurrentWindow `
    -ShiftControlV `
    -Text "你好"
```

### 4.7 等待画面稳定

等待屏幕内容不再变化（如 AI 回复流式输出结束），纯内存截屏对比，无磁盘写入：

```powershell
if (-not (& (Join-Path $Atoms "wait-stable.ps1") `
    -IntervalSecond 2 -Threshold 0.99 -TimeoutSecond 30)) {
    throw "画面未在 30 秒内稳定，终止工作流"
}
```

参数：

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `-IntervalSecond` | 1 | 两次截屏对比的间隔（秒） |
| `-Threshold` | 0.99 | 稳定判定阈值（像素匹配比例），0.99=允许 1% 像素变化 |
| `-TimeoutSecond` | 30 | 超时秒数，超时返回 `$false` |

画面稳定后返回 `$true`，超时返回 `$false`。

## 5. 组装 Series

参考 [`mouse-keyboard.example.ps1`](../series/mouse-keyboard.example.ps1)，在 `series/mine/` 创建小写短横线命名的脚本：

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Atoms = Join-Path $PSScriptRoot "..\atoms"

& (Join-Path $Atoms "start-app.ps1") -FilePath "<APP_EXE>"
& (Join-Path $Atoms "wait.ps1") -Seconds 2
& (Join-Path $Atoms "run-rpa.ps1") -Workflow "<WORKFLOW_JSON>"

Write-Host "[series] complete"
```

统一用以下方式启动。`-NoProfile` 是启动命令的一部分，不写进 Series 脚本或原子调用：

```powershell
pwsh -NoProfile -File series/mine/<series-name>.ps1
```

具体 Series 可以删除、重复或重新排列原子调用，但不能复制原子的内部实现。

## 6. 自定义原子规范

只有现有原子确实表达不了才新增。

- 一个原子只完成一个可独立验证的动作；
- 通过参数接收路径和业务数据，不写死具体软件或工作流；
- 成功时正常结束，失败时 `throw` 或返回非零退出码；
- 文件放在 `series/atoms/`，文件名使用小写短横线；
- 不修改与当前动作无关的原子。

## 7. 安全与失败规则

- RPA、键盘原子和目标软件必须用同一个 Windows 权限跑；
- 原子失败后立即停止，不忽略非零退出码；
- 路径、窗口标题、工作流或等待时间不明确时先询问，不能猜测；
- `-CurrentWindow` 只能在前一步已经保证正确窗口位于前台时使用；
- 具体脚本若使用 `exit 0`，必须确认它作为独立进程运行，不能被其他脚本点源加载。

## 8. 文档与语言规范

- 文件名：小写短横线，例如 `export-report.ps1`；
- PowerShell 参数：PascalCase，例如 `-WindowTitle`；
- 未确定值：大写占位符，例如 `<WORKFLOW_JSON>`；
- 进度日志：以 `[series]` 开头；
- 错误信息：说明失败步骤和目标对象；
- 文档说明使用中文；代码标识、命令和路径保持原文；
- 同一概念始终使用同一个名称。

## 9. 视觉模型边界

视觉模型当前不创建原子或模板。未来确定真实 CLI 后，才按原子规范接入：

```text
run-rpa 产出截图
    → 外部视觉 CLI 读取图片
    → 返回退出码和可选 JSON
    → Series 决定停止或继续
```

外部视觉工具不读取 RPA 工作流、不负责截图，也不在精确回放中实时决定点击位置。

## 10. 交付检查

Agent 完成 Series 后必须检查：

- [ ] 使用的程序和工作流路径真实存在；
- [ ] 没有遗留 `<PLACEHOLDER>`；
- [ ] 只读取并调用了需要的原子；
- [ ] 键盘目标和窗口前台条件明确；
- [ ] 等待策略符合目标软件特性；
- [ ] PowerShell Parser 未报告语法错误；
- [ ] 最终回复列出脚本路径、使用的原子和检查结果。
