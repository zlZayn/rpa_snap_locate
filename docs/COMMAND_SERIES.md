# Command Series：用脚本串联任意命令

## 核心思路

PowerShell 和 Bash 脚本本身就是轻量的命令编排器。任何能从终端运行的程序、脚本或 CLI 都可以成为一个步骤，本项目的 RPA 回放只是其中一种：

```text
准备文件 → 启动软件 → 回放 RPA → 执行 Python → 运行测试 → 发送通知
```

可以串联的内容没有固定清单，例如：

- 启动、关闭或配置桌面软件；
- 执行 Python、PowerShell、Bash、Node.js 等脚本；
- 调用 Git、uv、ffmpeg、curl 等 CLI；
- 复制文件、转换数据、构建项目或运行测试；
- 回放一个或多个已录制的 RPA 工作流；
- 在流程结束后归档结果或发送通知。

只要命令有明确的参数、退出状态和完成边界，就可以放进同一个 Series。以下 RPA 命令就是一个普通的前台步骤：

```powershell
uv run python main.py run data/workflows/<workflow>.json
```

它会等待回放完成后退出，然后脚本继续执行下一步。其他前台命令遵循同样的串行规则；需要长期运行的 GUI 或服务则在后台启动，再显式等待其就绪。

可直接复制以下模板：

- [`examples/series.template.ps1`](../examples/series.template.ps1)：Windows / PowerShell，推荐本项目使用；
- [`examples/series.template.sh`](../examples/series.template.sh)：Bash、Git Bash 或类 Unix 环境。

生成的具体流程统一保存到 `examples/series/`：

```text
examples/
├── series.template.ps1          # PowerShell 规范源
├── series.template.sh           # Bash 规范源
└── series/
    ├── <series-name>.ps1        # 生成的 PowerShell 流程
    └── <series-name>.sh         # 生成的 Bash 流程
```

`<series-name>` 使用小写短横线命名，例如 `open-editor-and-export.ps1`。模板文件只维护公共函数和结构，具体软件路径与工作流组合放在 `examples/series/`，避免修改模板本身。

## PowerShell 串联规则

| 写法 | 含义 | 适用场景 |
| :--- | :--- | :--- |
| `& command @args` | 调用一个命令或脚本 | 路径或参数保存在变量中 |
| `a; b` | 执行 `a` 后总是执行 `b` | 不关心上一步是否失败 |
| `a && b` | `a` 成功后才执行 `b` | PowerShell 7+ 的简单串联 |
| `Start-Process` | 启动独立进程并立即继续 | 打开 GUI 软件 |
| `Start-Process -Wait` | 启动进程并等待它退出 | 安装器、一次性工具 |

这里的 `&` 是调用运算符，不是 Bash 中的“放到后台”。复杂工作流不要写成一条超长命令；用一行一个动作的 `.ps1` 更容易处理路径、日志和错误。

### 最小示例

```powershell
$ErrorActionPreference = "Stop"

Start-Process -FilePath "notepad.exe" -WindowStyle Maximized
Start-Sleep -Seconds 2

uv run python main.py run "data/workflows/notepad.json"
if ($LASTEXITCODE -ne 0) { throw "notepad workflow failed" }

Start-Process -FilePath "calc.exe"
Start-Sleep -Seconds 2

uv run python main.py run "data/workflows/calculator.json"
if ($LASTEXITCODE -ne 0) { throw "calculator workflow failed" }
```

`-WindowStyle Maximized` 对大多数传统桌面程序有效；部分 Chromium、UWP 或自带窗口管理的软件可能忽略它。这类软件可以使用自身的 `--start-maximized` 参数，或把最大化操作录入回放步骤。

优先把 GUI 软件自身的 `.exe` 传给 `Start-SeriesApp`。`.cmd` / `.bat` 会由 `cmd.exe` 承载，并且可能等待 GUI 软件整个生命周期，造成黑色控制台窗口一直存在。模板检测到这两类启动器时会隐藏其控制台宿主；具体 Series 如果已知真实 GUI 可执行文件，应直接改用 `.exe`。

### Windows 权限边界

Windows UIPI 会拒绝低完整性级别进程向高完整性级别窗口注入鼠标事件。因此，目标软件和 `uv run python main.py run ...` 必须以相同权限运行，建议默认都不使用管理员权限。目标窗口标题含 `[Administrator]` / `管理员`，或者目标软件确实必须提升权限时，应提升整个 Series，使软件启动和 RPA 回放共享同一权限上下文。通用模板不会自动提权；具体 Series 可以在启动任何子进程前完成一次自举提权。

光标成功移动不代表点击已被目标窗口接受。核心执行器检查 `SendInput` 的返回值，注入被拒绝时会终止回放并提示权限不一致，而不是继续执行后续步骤。

## Bash 串联规则

| 写法 | 含义 |
| :--- | :--- |
| `a; b` | 无论 `a` 是否成功都执行 `b` |
| `a && b` | 仅当 `a` 成功时执行 `b` |
| `a &` | 在后台启动 `a`，脚本立即继续 |
| `a & pid=$!; wait "$pid"` | 后台启动并在稍后等待 |
| `set -Eeuo pipefail` | 未处理错误、未定义变量或管道失败时停止 |

### 最小示例

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

notepad.exe &
sleep 2
uv run python main.py run "data/workflows/notepad.json"

calc.exe &
sleep 2
uv run python main.py run "data/workflows/calculator.json"
```

Bash 下如何最大化窗口取决于运行环境。例如 Linux/X11 可以使用 `wmctrl`，Git Bash 调用 Windows GUI 时则更适合把窗口准备动作放进 PowerShell 小函数或录制工作流。

## 推荐的 Series 结构

模板提供四个小函数，它们只是常见操作的便捷封装，不限制 Series 中能执行的命令：

1. `Invoke-SeriesCommand` / `run_command`：执行任意前台命令，并在失败时停止；
2. `Start-SeriesApp` / `start_app`：在后台启动 GUI 软件或长期进程；
3. `Wait-SeriesReady` / `wait_ready`：等待固定时间或明确的就绪条件；
4. `Invoke-SeriesRpa` / `run_rpa`：回放指定 JSON，是针对本项目的便捷适配器。

普通命令可以直接写在脚本中，也可以通过通用函数获得统一日志和错误处理。重复出现且有独立校验逻辑的命令，再封装为类似 `Invoke-SeriesRpa` 的专用函数。Series 只负责步骤之间的顺序和边界，每个组件仍可独立替换。

### 任意命令示例

```powershell
Invoke-SeriesCommand -Name "prepare input" -FilePath "python" -ArgumentList @(
    "scripts/prepare.py",
    "--input",
    "data/input.json"
)

Invoke-SeriesRpa -Workflow "data/workflows/editor.json"

Invoke-SeriesCommand -Name "run tests" -FilePath "uv" -ArgumentList @(
    "run",
    "python",
    "-m",
    "unittest",
    "discover"
)
```

## 等待策略

GUI 软件通常由启动命令在后台运行，而 RPA 必须等界面可操作后才能开始。按可靠性从高到低选择：

1. 等待目标窗口出现并可激活；
2. 等待目标进程和窗口句柄；
3. 等待文件、端口或其他业务就绪信号；
4. 最后才使用固定 `Start-Sleep` / `sleep`。

当前模板使用固定等待以保持零额外依赖。流程稳定后，可以只替换 `Wait-SeriesReady`，不需要修改其他步骤。

## 错误处理

- GUI 启动失败：立即停止，不要继续向错误窗口发送点击；
- RPA 回放返回非零退出码：停止 Series，并输出工作流路径；
- 可恢复步骤：在函数外显式重试，避免所有命令被无条件重复；
- 路径：脚本先切换到项目根目录，避免从不同目录启动时找不到 `main.py` 或 JSON；
- 日志：每一步开始和结束都输出稳定名称，方便定位失败位置。

## 使用前提

在让 AI 生成串联脚本前，必须先确认两件事：

1. **录制文件是否已存在** — 回放依赖 `data/workflows/` 下的 JSON 文件，必须先录制或确认已有；
2. **文件路径是否正确** — 指定给 AI 的工作流路径必须是真实存在的文件，否则脚本会在 `Invoke-SeriesRpa` / `run_rpa` 中报错退出。

Windows 下还要确认目标软件与回放脚本的权限级别一致，并优先提供 GUI `.exe` 路径而不是 `.cmd` / `.bat` 启动器。

AI 生成脚本后，如果它使用了 `<PLACEHOLDER>` 占位，你需要提供具体的程序路径、窗口标题和已录制 JSON 路径。

## 给 AI 的生成指令

```text
请把我的多命令任务生成为 Series 脚本并保存到项目中。任务可以包含任意 CLI、脚本、GUI 软件和 RPA 回放，不要把 Series 限制为桌面自动化。

输入：
- TARGET_SHELL: <powershell|bash>
- SERIES_NAME: <小写短横线名称>
- TASK: <描述要按顺序执行的命令、脚本、软件、RPA 回放和最终结果>

执行规则：
1. 第一步必须完整阅读对应模板，确认现有函数签名：
   - powershell：examples/series.template.ps1
   - bash：examples/series.template.sh
2. 检查 TASK 引用的工作流文件是否真实存在；缺失时先向用户确认，不猜测路径。
3. 基于模板生成脚本，不重新发明同用途函数，也不改变模板的错误处理方式：
   - 任意前台命令使用 Invoke-SeriesCommand / run_command；
   - GUI 或长期进程使用 Start-SeriesApp / start_app；
   - 就绪等待使用 Wait-SeriesReady / wait_ready；
   - RPA 回放使用 Invoke-SeriesRpa / run_rpa。
4. 前台命令按书写顺序执行；GUI 软件或长期进程在后台启动，并在后续步骤依赖它们时显式等待就绪。
5. RPA 命令统一为 uv run python main.py run <JSON路径>。
6. 路径放在参数或脚本顶部变量中并正确引用；禁止 eval 和命令字符串拼接。
7. 默认任一步失败就停止；不得忽略 PowerShell 的 $LASTEXITCODE 或 Bash 的非零退出码。
8. 不确定的程序路径、等待时间和工作流路径使用 <PLACEHOLDER>，不得虚构实际值。
9. 将结果直接保存到：
   - powershell：examples/series/<SERIES_NAME>.ps1
   - bash：examples/series/<SERIES_NAME>.sh
10. 保存后执行语法检查：PowerShell 使用语言 Parser，Bash 使用 bash -n。
11. 最终回复只需给出产物路径、语法检查结果和仍需替换的占位符。
```

## 什么时候才需要独立 runner

当出现以下情况时，再考虑增加一个极小的 `series run`：

- 大量脚本需要统一重试、超时和结构化日志；
- 需要从别的程序动态拼装步骤，而不是人工维护脚本；
- 需要跨 PowerShell 和 Bash 使用同一份流程定义；
- 需要暂停、恢复或可视化执行状态。

在此之前，原生脚本本身就是最轻、最透明、最好调试的 Series runner。
