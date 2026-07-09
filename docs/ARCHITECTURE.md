# Visual RPA Recorder -- Architecture

Pure-visual desktop automation recorder and replay tool. Fixed-coordinate + screenshot-region positioning, with pluggable LLM slot.

---

## Entry Points

Two modes via `main.py`, dispatched by argv:

- `uv run python main.py` — recording mode (interactive, hotkey-driven)
- `uv run python main.py run data/workflows/<name>.json` — replay mode (headless, runs and exits)

### Recording mode (`cmd_record()`)

Wires ConfigManager + RecorderEngine + HotkeyRegistry. Registers F2/F3/ESC/Ctrl+S/F5 as hotkey callbacks, then blocks on `keyboard.wait()`. F5 triggers replay via daemon thread calling PipelineRunner, reading the most recent json from `data/workflows/`.

### Replay mode (`cmd_run(workflow_path)`)

Loads the given JSON file path and runs PipelineRunner directly. No hotkeys, no blocking. Exits after execution.

---

## Layers & Dependency Direction

Strictly one-way — no layer imports from above, no circular imports.

```text
main.py              → engine + config + utils
engine               → core + data + config
core                 → config + utils
data                 → config
config               → stdlib + yaml only
utils                → stdlib only
```

---

## Directory Map

```text
rpa_snap_locate/
├── main.py                     Entry          Two-mode dispatcher: record / run
├── config/
│   ├── system.yaml                             Screen, paths (YAML)
│   └── config_manager.py        Config         Singleton loader, dotted-key access
├── engine/
│   ├── recorder_engine.py        Orchestration  State machine (IDLE / WAITING_SECOND / WAITING_TARGET)
│   ├── step_builder.py           Orchestration  Builds fixed-click and screenshot-click step dicts
│   ├── hotkey_registry.py        Orchestration  Wraps keyboard library, register/dispatch
│   └── pipeline_runner.py        Orchestration  Iterates steps, locates, clicks, saves screenshots + snapshots
├── core/
│   ├── perception_provider.py     Domain        Screen capture (mss), mouse/DPI/window info
│   ├── locator_protocol.py        Domain        BaseLocator ABC + create_locator() factory
│   ├── locators/
│   │   ├── fixed_locator.py       Domain        [ACTIVE] norm_x/norm_y to physical coords
│   │   ├── template_locator.py    Domain        [ACTIVE] ScreenshotLocator: region + offset to coords
│   │   └── llm_locator.py         Domain        [STUB] Future multimodal LLM locator
│   ├── action_executor.py         Domain        [ACTIVE] pyautogui click/write, failsafe disabled
│   └── change_validator.py        Domain        [STUB] dHash change detection
├── data/
│   ├── data_manager.py            Persistence   Workflow JSON persistence (workflows dir)
│   ├── recordings/                Data          Per-session dirs with screenshots/ and snapshots/
│   └── workflows/                 Data          JSON workflow files, named as {ts}-{N}steps.json
├── utils/
│   ├── dpi_calculator.py          Tool          DPI detection + coordinate conversion
│   ├── logger_setup.py            Tool          RotatingFileHandler + console handler
│   ├── hash_calculator.py         Tool          [STUB] dHash fingerprint
│   └── image_entropy_calculator.py  Tool        [STUB] Shannon entropy
├── logs/
│   └── recorder.log               Output        Runtime log
├── tests/                          Tests        Ready for future use
└── pyproject.toml                  Build        uv project, 6 dependencies
```

Naming convention: `domain_role.py` — suffixes `_manager`, `_provider`, `_protocol`, `_engine`, `_builder`, `_registry`, `_executor`, `_validator`, `_calculator`.

---

## Data Directory Layout

```text
data/
  recordings/
    20260709_221848-4steps/
      20260709_221848/                    # run timestamp — recording or replay
        screenshots/                       # F3-cropped region screenshots
          step_0001.png
        snapshots/                         # red-cross evidence
          step_0001_before.png
          step_0001_after.png
      20260709_222504/                    # another replay run
        screenshots/
          step_0001.png
        snapshots/
          step_0001_before.png
          step_0001_after.png
  workflows/
    20260709_221848-4steps.json           # json lives here, separate from recordings
```

Recording produces only a JSON file in `data/workflows/` — no images. Images are generated exclusively during replay: each replay creates a self-contained `{run_ts}/` directory under `recordings/{dir_name}/` with `screenshots/` and `snapshots/`.

---

## Module-by-Module

### Config — `config/config_manager.py` + `config/system.yaml`

Singleton via `__new__`. Methods: `load(path)` parses YAML, `get(*keys, default)` traverses nested dict, `reload()` resets. Used by PerceptionProvider, RecorderEngine, DataManager, PipelineRunner, main.py.

| Section | Key | Default | Description |
| :--- | :--- | :--- | :--- |
| `screen` | `logical_width`, `logical_height`, `dpi_scale` | 1920×1080, auto | Screen resolution and DPI |
| `paths` | `recordings_dir`, `workflows_dir`, `logs_dir` | data/... | Data directory paths |
| `recorder` | `box_select_timeout_seconds` | 10 | Box-select mode timeout |
| `replay` | `start_delay_seconds` | 0 | Delay before first step executes |

### Engine — `engine/recorder_engine.py`

Central state machine. States: IDLE, WAITING_SECOND, WAITING_TARGET.

Transitions:
- IDLE + F2: stays IDLE, builds fixed-click step via StepBuilder
- IDLE + F3: records `_box_point1`, transitions to WAITING_SECOND
- IDLE + ESC: no-op
- WAITING_SECOND + F3: records `_box_point2`, computes box region in memory, transitions to WAITING_TARGET (no screenshot saved) — screenshot is taken at replay time
- WAITING_SECOND + ESC: clears box state, returns to IDLE
- WAITING_TARGET + F2: captures offset, builds screenshot-click step, returns to IDLE
- WAITING_TARGET + ESC: clears box state, returns to IDLE
- Any state + `clear()`: wipes steps, counter, returns to IDLE

Public API: `on_f2()`, `on_f3()`, `on_cancel()`, `save()`, `clear()`, `use_box_center()`. Properties: `steps` (copy), `step_count`.

On construction, records a timestamp from `DataManager.new_recording()`. On save, writes the step list as JSON to `workflows/{ts}-{N}steps.json`. No filesystem directories or images are created during recording.

### Engine — `engine/step_builder.py`

Owns auto-increment `_step_counter`. Two methods:
- `build_fixed_click_step()`: sensor data → `{index, action, method:"fixed", norm_x, norm_y, ...}`
- `build_screenshot_click_step(region, offset_x, offset_y)`: → `{index, action, method:"screenshot", region, offset_x, offset_y, ...}` (no `screenshot_path` — screenshot is captured at replay time)

### Engine — `engine/hotkey_registry.py`

Thin wrapper: `register(hotkey, callback)` calls `keyboard.add_hotkey`, `start_listening()` calls `keyboard.wait()` (with `KeyboardInterrupt` catch for clean Ctrl+C exit), `remove_all()` calls `keyboard.unhook_all()`.

### Engine — `engine/pipeline_runner.py`

[ACTIVE] Reads workflow JSON from given path. On start, respects `replay.start_delay_seconds` from `system.yaml` (default 0 — no delay) — a brief pause before executing the first step, giving the user time to switch to the target window.

Creates a new `{run_ts}/` directory under `recordings/{dir_name}/`. For each step: calls `create_locator(method)`, `locator.locate(step)` for coords, captures before-screen via `capture_screen()`, clicks via `ActionExecutor`, captures after-screen. Saves before/after with red cross to `snapshots/`. If step has a `region`, re-captures the region screenshot and saves to `screenshots/`.

This is the sole producer of all image files (screenshots + snapshots). Recording mode produces JSON only — no images written until replay.

Resolves recording dir from json filename (`{dir_name}.json` → `recordings/{dir_name}/{run_ts}/`). Falls back to `dirname(workflow_path)/{run_ts}/` if filename doesn't match convention.

Used by both F5 hotkey (recording mode, daemon thread) and `cmd_run` (replay mode, blocking).

### Core — `core/perception_provider.py`

All hardware access centralized. Six methods:
- `capture_screen()`: mss → PIL.Image
- `capture_region(l,t,w,h)`: mss → PIL.Image
- `get_mouse_position()`: pyautogui → (phys_x, phys_y)
- `get_active_window()`: pygetwindow → {title, hwnd, left, top, width, height}
- `get_dpi_scale()`: config override or OS detection
- `get_logical_resolution()`: if not in config, returns `physical / dpi_scale`

### Core — `core/locator_protocol.py`

```python
class BaseLocator(ABC):
    @abstractmethod
    def locate(self, step: dict) -> tuple[int, int]: ...
```

`create_locator(method)`: lazy import factory, maps `"fixed"` → FixedLocator, `"screenshot"` → ScreenshotLocator, `"llm"` → LLMLocator.

### Core — Locator Implementations

- **FixedLocator**: reads `step["norm_x/y"]`, converts via `normalized_to_phys()`. [ACTIVE]
- **ScreenshotLocator**: reads `step["region"]` + `step["offset_x/y"]`, returns `(left + offset_x, top + offset_y)`. Region coordinates are absolute — no template matching. [ACTIVE]
- **LLMLocator**: NotImplementedError. [STUB]

### Core — `core/action_executor.py`

[ACTIVE] Wraps pyautogui, disables failsafe corner detection. `click(x, y)` calls `pyautogui.click`. `type_text(text)` calls `pyautogui.write` with 50ms interval.

### Core — `core/change_validator.py`

[STUB] NotImplementedError.

### Data — `data/data_manager.py`

Handles JSON persistence for workflows. Also ensures `workflows_dir` exists on init.
- `new_recording()`: records a session timestamp string
- `save_workflow(steps, session_name)`: writes `{workflows_dir}/{ts}-{N}steps.json`

All image I/O is handled by PipelineRunner during replay — DataManager has zero involvement in screenshot or snapshot storage.

---

## Data Formats

### `data/workflows/{ts}-{N}steps.json`

```json
{
  "version": "4.0",
  "created_at": "2026-07-09T10:30:00",
  "steps": [
    {
      "index": 1,
      "action": "click",
      "method": "fixed",
      "norm_x": 0.35,
      "norm_y": 0.42,
      "window_title": "记事本",
      "dpi_scale": 1.5
    },
    {
      "index": 2,
      "action": "click",
      "method": "screenshot",
      "region": {"left": 500, "top": 300, "width": 120, "height": 40},
      "offset_x": 60,
      "offset_y": 20,
      "window_title": "记事本",
      "dpi_scale": 1.5
    }
  ]
}
```

No `screenshot_path` in json — region screenshots are captured fresh each replay.

---

## Per-Run Directory

Each run (recording or replay) lives in `recordings/{session}/{run_ts}/`:
- `screenshots/step_{index:04d}.png` — region screenshot re-captured each replay
- `snapshots/step_{index:04d}_before.png` — before-click full screen with red cross at click pos
- `snapshots/step_{index:04d}_after.png` — after-click full screen with red cross at click pos

---

## Stub Modules

| File | Future Purpose |
| :--- | :--- |
| `change_validator.py` | `wait_for_change(before_hash)` — polls dHash with exponential backoff |
| `llm_locator.py` | Multimodal LLM API call (screenshot → base64 → prompt → JSON → coords) |
| `hash_calculator.py` | dHash for fast screen-change detection |
| `image_entropy_calculator.py` | Shannon entropy for auto-selecting high-texture anchors |

---

## Runtime

| Item | Detail |
| :--- | :--- |
| Python | >= 3.11 |
| Package manager | uv |
| Admin rights | Required (Windows) — keyboard library needs SE_CREATE_GLOBAL_NAME |
| Run | `uv run python main.py` (project root) |
| Hotkeys | F2 (click), F3 (box), ESC (cancel), Ctrl+S (save), F5 (replay). Hardcoded in `main.py` |
| Dependencies | mss, pygetwindow, pyautogui, keyboard, pyyaml, pillow |