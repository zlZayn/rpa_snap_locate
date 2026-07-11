# RPA Snap Locate

[English](README.md) | [简体中文](README_zh.md)

Pure-visual desktop automation recorder and replay tool. Fixed-coordinate + screenshot-region positioning, with pluggable LLM slot.

## Quick Start

```bash
uv sync
uv run python main.py                        # record mode (hotkey-driven)
uv run python main.py run data/workflows/<file>.json  # replay mode
```

## Hotkeys (Record Mode)

| Hotkey | Function |
| :--- | :--- |
| F2 | Record a click step at mouse position |
| F3 | Two-press box selection for region recording |
| ESC | Cancel current box selection |
| Ctrl+S | Save the current workflow and start a new recording |
| F5 | Replay the latest workflow |

> During box selection (after first F3), pressing F2 sets a precise click target inside the box; pressing ESC uses the box center as default.

Each save contains only the steps recorded since launch or the previous save. After a successful save, step numbering and any in-progress box selection are reset for a new workflow. Pressing Ctrl+S with no recorded steps does nothing.

## Replay

```bash
uv run python main.py run <workflow.json>
```

The pipeline waits `replay.start_delay_seconds` (default 0 — configurable in `config/system.yaml`) before executing the first step, giving you time to switch to the target window.

Images (screenshots + before/after snapshots) are generated only during replay — recording produces only JSON.

On Windows, the replay process and target application must run at the same privilege level. Windows blocks simulated input from a normal process into an administrator window. Prefer running both normally; if the target must be elevated, elevate the replay process too. A rejected click is reported as an error instead of being logged as successful.

## Series

Chain app launches and RPA replays into a single script — easy for AI agents to generate and execute. See [`examples/series.template.ps1`](examples/series.template.ps1) (PowerShell), [`examples/series.template.sh`](examples/series.template.sh) (Bash), or [`docs/COMMAND_SERIES.md`](docs/COMMAND_SERIES.md).

On Windows, launch the application's GUI `.exe` directly when possible. A `.cmd` or `.bat` launcher may keep its console host open for the application's entire lifetime; the PowerShell template hides that host when such a launcher is required.

## Directory Layout

```text
data/
  recordings/[{name}-]{timestamp}-{N}steps/
    {run_timestamp}/
      screenshots/               # region screenshots (re-captured on replay)
      snapshots/                 # red-cross evidence (before + after)
  workflows/[{name}-]{timestamp}-{N}steps.json  # workflow JSON; name is optional
```

## Configuration

Edit `config/system.yaml`:

| Section | Key | Default | Description |
| :--- | :--- | :--- | :--- |
| `screen` | `logical_width`, `logical_height` | 1920, 1080 | Logical resolution |
| `screen` | `dpi_scale` | auto | DPI scaling factor |
| `replay` | `start_delay_seconds` | 0 | Delay before first step executes |

## Requirements

- Python >= 3.11
- uv (package manager)
- Windows record mode may require administrator rights for global hotkeys
- Replay and the target application must use the same Windows privilege level
