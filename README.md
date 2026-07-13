# RPA Snap Locate

[English](README.md) | [简体中文](README_zh.md)

A small Windows tool that records mouse actions and plays them back later.

## What it records

- When each mouse button is pressed and released;
- The real time between actions, including fast double-clicks;
- Left, right, and middle mouse buttons;
- Click positions with support for common screen scaling;
- Area selections with F3 for targeted screenshots during replay;
- A before picture, an after picture, and a timing report for every replay;
- An optional mode that saves click positions and order without action timing.

## Quick start

Install the requirements:

```bash
uv sync
```

Start recording mode:

```bash
uv run python main.py
```

There is one main flow to remember:

1. Press F2 to start.
2. Use the mouse normally. Double-click at your normal speed.
3. Press Ctrl+S to save (it stops recording first if active).
4. Press F5 to replay the saved file.

Timing starts when F2 starts recording, so replay also preserves the wait before the first mouse action. Pressing F2 to stop and then Ctrl+S works the same way. Press F2 between segments only when you want to record in parts and save everything at once. Time between segments is not recorded; timing resumes only after F2 starts the next segment.

You can also replay a chosen file:

```bash
uv run python main.py run data/workflows/<file>.json
```

## Recording keys

| Key | Action |
| :--- | :--- |
| Ctrl+Delete | Clear unsaved recording data |
| Ctrl+S | Save (stops recording first if active) |
| ESC | Cancel an area selection in progress |
| F1 | Show this help |
| F2 | Start recording; press again to stop and keep events for continued recording |
| F3 | Area selection: press F3 twice to mark a rectangle for screenshot capture during replay; recording continues normally |
| F5 | Replay the most recently saved file |

### Selecting a capture area

Press F2 to start recording, then:

1. Move to one corner of the area and press F3.
2. Move to the opposite corner and press F3 again.

The area is added as a screenshot event in the timeline and captured at the right moment during replay, without affecting how click positions are recorded. Click positions always use absolute screen coordinates. Multiple areas can be marked. The area images are saved to `data/recordings/`.

## If a message is unclear

- F3 says it cannot be used: press F2 first, then select the area.
- Saving says a mouse button was not released: press Ctrl+Delete and record again.
- F5 says there are unsaved actions: press Ctrl+S to save or Ctrl+Delete to discard them.
- To see which file was saved, read the full path printed after a successful save.
- If you forget the keys, press F1 to show the main flow again.

## Replay results

Saved recordings are stored in:

```text
data/workflows/
```

Each replay stores its before picture, after picture, and timing report in:

```text
data/recordings/<recording-name>/<replay-time>/
```

If an action runs much later than planned, `replay_report.json` marks the replay as `degraded`. This usually means the computer was busy, switching windows was slow, or the recorded actions were extremely close together.

## Common settings

Edit `config/system.yaml`:

| Setting | Default | Purpose |
| :--- | :--- | :--- |
| `recorder.mode` | `timeline` | `timeline` keeps action timing; `legacy` saves only click positions and order |
| `recorder.event_queue_limit` | `10000` | Maximum number of mouse events held during one recording |
| `replay.start_delay_seconds` | `0` | Wait before replay starts so you can switch windows |
| `replay.late_warning_ms` | `10` | Report actions that run this many milliseconds late |

Most users only need `start_delay_seconds`. Set it to `2`, for example, to wait two seconds before playback begins.

## Windows permissions

The replay tool and target application must use the same permission level:

- If the target runs normally, run this tool normally.
- If the target runs as administrator, run this tool as administrator too.

Windows rejects mouse actions when the permission levels do not match. The tool reports the error instead of claiming the click succeeded.

## Start an app and replay automatically

To open an application, wait for it, and then run a recording, see:

- [PowerShell composition example](series/mouse-keyboard.example.ps1)
- [Atomic scripts to compose as needed](series/atoms/)
- [Series guide](docs/COMMAND_SERIES.md)

On Windows, launch the application's `.exe` file directly when possible.

This project does not record keyboard input or support dragging. When keyboard input is needed, run AutoHotkey, PowerShell, or another command-line keyboard automation script as a separate Series step before, between, or after mouse workflows; see the [Series guide](docs/COMMAND_SERIES.md).

## Requirements

- Windows
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)

For module relationships, recording states, file formats, and playback timing, read the [architecture guide](docs/ARCHITECTURE.md).
