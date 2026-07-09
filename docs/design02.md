# 项目技术设计文档：轻量级视觉驱动自动化框架

**版本**：V4.0（融合定稿版）
**核心语言**：Python
**设计哲学**：骨架面向未来，实现立足当下；组件可插拔，记录即配置。

---

## 一、项目目标与边界

### 1.1 核心目标

构建一个**纯视觉驱动**的桌面自动化工具，支持**先录制、后回放**的完整工作流。

- **当前阶段**：只实现录制功能（F2/F3 快捷键采集操作步骤）
- **后续阶段**：回放执行器（基于录制的配置进行自动化操作）
- **远期扩展**：可选接入多模态大模型（LLM），替代或辅助固定坐标定位

### 1.2 能力边界

| 维度 | 能做到 | 不涉及 |
| :--- | :--- | :--- |
| **操作对象** | Windows/macOS 图形界面（Win32, Qt, Web） | 命令行终端、无UI后台服务 |
| **采集模式** | F2 录制单击坐标；F3 录制矩形截图区域（对角两点） | 连续动作流录制、拖拽路径 |
| **截图存储** | F3 框选区域自动截取 PNG 模板图 | 预处理、自动锚点选取 |
| **输出格式** | `workflow.json` 步骤序列 + `templates/` 模板图 | 执行回放（后续实现） |
| **LLM集成** | 预留接口，可插拔接入 | 当前不实现 |

---

## 二、整体架构（三层分离 + 双环容错）

框架采用 **"感知-定位-执行"** 三层解耦 + **"外环调度/内环原子动作"** 双环设计。

```text
[ 输入: workflow.json ]
         ↓
┌──────────────────────────────────────────────────────┐
│             外环 (Pipeline 调度器)                     │
│  - 顺序遍历步骤列表                                     │
│  - 异常捕获与隔离（单步失败不中断整体）                 │
│  - 任务级重试（指数退避）                              │
└──────────────────────────────────────────────────────┘
         ↓ (逐项分发)
┌──────────────────────────────────────────────────────┐
│        内环 (原子动作执行器 - Atomic Actor)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐ │
│  │ 感知模块 │→│ 定位模块 │→│ 执行模块 │→│ 验证 │ │
│  │ (截图/   │  │(Locator) │  │(Action)  │  │(dHash│ │
│  │ DPI/窗口)│  │ 可插拔   │  │          │  │比对) │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────┘ │
└──────────────────────────────────────────────────────┘
         ↑
[ 录制器 (当前激活) ]
  F2/F3 → 感知模块 → 构造步骤 → 写入 workflow.json
```

**当前阶段**：仅使用录制器 + 感知模块（红线以上是空壳骨架，保留待用）。

---

## 三、录制器详细设计（当前实现）

### 3.1 快捷键总览

| 快捷键 | 功能 | 状态依赖 |
| :--- | :--- | :--- |
| **F2** | 录制单步点击坐标（固定模式） | 无（随时可用） |
| **F3** | 开始/结束矩形框选截图 | 状态机：第一次按 → 第二次按 |
| **ESC** | 取消当前框选操作 | 仅在框选状态中有效 |
| **Ctrl+S** | 保存当前工作流到 `workflow.json` | 步骤列表不为空 |

### 3.2 F2 — 录制单步点击坐标

**操作流**：

1. 用户将鼠标移动到目标元素上
2. 按 F2
3. 录制器捕获：
   - 当前鼠标物理坐标 `(phys_x, phys_y)`
   - 当前活动窗口句柄和标题
   - 当前系统 DPI 缩放比例
4. 计算逻辑归一化坐标：
   - `norm_x = phys_x / 逻辑屏幕宽度`
   - `norm_y = phys_y / 逻辑屏幕高度`
5. 构造步骤对象：

```json
{
  "action": "click",
  "method": "fixed",
  "norm_x": 0.35,
  "norm_y": 0.42,
  "window_title": "记事本",
  "dpi_scale": 1.5
}
```

1. 追加到内存中的步骤列表，终端输出反馈。

### 3.3 F3 — 录制矩形截图区域

**状态机**（三个状态）：

- **IDLE** → 第一次 F3：记录 `(x1, y1)`，状态变为 `WAITING_SECOND`
- **WAITING_SECOND** → 第二次 F3：记录 `(x2, y2)`，计算矩形，截图并保存模板，状态变为 `WAITING_TARGET`
- **WAITING_TARGET** → F2：记录目标点击偏移量，生成步骤，回到 IDLE。ESC：取消，回 IDLE。10秒超时自动取消。

**步骤对象**（模板定位模式）：

```json
{
  "action": "click",
  "method": "template",
  "template_path": "templates/step_003.png",
  "region": { "left": 100, "top": 200, "width": 80, "height": 30 },
  "offset_x": 40,
  "offset_y": 15,
  "window_title": "...",
  "dpi_scale": 1.5
}
```

- `offset_x/offset_y` 为目标点击点相对于模板区域左上角的偏移
- 若用户没有按 F2 指定目标点，默认使用矩形中心

### 3.4 感知模块公共接口

所有硬件信息采集统一走感知模块：

```python
# core/perception.py
capture_screen()          # → PIL.Image  全屏截图
get_mouse_position()      # → (x, y)     物理坐标
get_active_window()       # → {title, hwnd, left, top, width, height}
get_dpi_scale()           # → float      如 1.0, 1.25, 1.5, 2.0
get_logical_resolution()  # → (w, h)     逻辑像素
```

---

## 四、可插拔定位模块设计（核心接口）

这是保证"后续装LLM不麻烦"的关键设计。

### 4.1 抽象基类

```python
# core/locator.py
class BaseLocator(ABC):
    @abstractmethod
    def locate(self, step: dict) -> tuple[int, int]:
        """根据步骤配置，返回物理坐标 (x, y)"""
```

### 4.2 实现A：FixedLocator（当前使用）

直接读取 `step` 中的 `norm_x/norm_y`，结合当前屏幕逻辑分辨率反算物理坐标。零成本、无依赖。

```python
class FixedLocator(BaseLocator):
    def locate(self, step):
        norm_x = step["norm_x"]
        norm_y = step["norm_y"]
        logical_w, logical_h = get_logical_resolution()
        phys_x = int(norm_x * logical_w * get_dpi_scale())
        phys_y = int(norm_y * logical_h * get_dpi_scale())
        return phys_x, phys_y
```

### 4.3 实现B：TemplateLocator（可选实现）

使用 `cv2.matchTemplate` 在全屏截图中搜索模板图，返回匹配位置 + 偏移量。

```python
class TemplateLocator(BaseLocator):
    def locate(self, step):
        template_path = step["template_path"]
        screenshot = capture_screen()
        # cv2.matchTemplate 匹配
        # 加上 step["offset_x/y"]
        return match_x, match_y
```

### 4.4 实现C：LLMLocator（预留接口，当前不实现）

```python
class LLMLocator(BaseLocator):
    """录制时若 method=llm，定位器调用多模态模型解析坐标。
    当前只作为接口占位，不实现任何逻辑。"""
    def locate(self, step):
        # TODO: 截全屏 → 转Base64 → 构造Prompt → 调用API → 解析坐标
        raise NotImplementedError("LLM定位器尚未实现")
```

### 4.5 工厂函数

```python
def create_locator(method: str) -> BaseLocator:
    mapping = {
        "fixed": FixedLocator,
        "template": TemplateLocator,
        "llm": LLMLocator,    # 注册但未实现
    }
    cls = mapping.get(method)
    if cls is None:
        raise ValueError(f"未知定位方式: {method}")
    return cls()
```

**切换定位方式只需改 `workflow.json` 中步骤的 `method` 字段，或改工厂映射，其他模块零修改。**

---

## 五、执行模块 & 验证模块（骨架预留）

当前版本**不实现**，仅保留空壳文件和类定义，供后续回放开发。

```python
# core/action.py
class ActionExecutor:
    def click(self, x, y):     raise NotImplementedError
    def type_text(self, text):   raise NotImplementedError

# core/validator.py
class Validator:
    def wait_for_change(self, before_hash):  raise NotImplementedError

# engine/runner.py
class PipelineRunner:
    def run(self, workflow_path):  raise NotImplementedError
```

---

## 六、录制器录制LLM步骤的数据流

虽然当前不实现LLM，但录制器在设计上已经**允许以后录制LLM步骤**：

录制时按 F2/F3 采集数据和截图，`method` 字段设为 `"llm"`，同样写入 `workflow.json`。回放时工厂根据 `"llm"` 实例化 `LLMLocator`，完全不需要修改录制器代码。

```json
{
  "action": "click",
  "method": "llm",
  "instruction": "点击页面上名称为'提交'的蓝色按钮",
  "norm_x": 0.0,
  "norm_y": 0.0,
  "window_title": "...",
  "dpi_scale": 1.5
}
```

录制器不关心 `method` 的语义，只负责按当前模式封装数据。

---

## 七、配置文件与数据格式

### 7.1 `config/system.yaml`

```yaml
screen:
  logical_width: 1920       # 可覆盖自动检测值
  logical_height: 1080
  dpi_scale: 1.5

hotkeys:
  record_click: F2
  record_box_start: F3
  cancel: ESC
  save: ctrl+s

paths:
  workflow: tasks/workflow.json
  templates_dir: tasks/templates/
  logs_dir: logs/
```

### 7.2 `tasks/workflow.json`

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
      "method": "template",
      "template_path": "templates/step_002.png",
      "region": {"left": 500, "top": 300, "width": 120, "height": 40},
      "offset_x": 60,
      "offset_y": 20,
      "window_title": "记事本",
      "dpi_scale": 1.5
    }
  ]
}
```

---

## 八、项目目录结构

```text
visual_rpa/
│
├── main.py                              # 入口：启动录制器，监听全局热键
│
├── config/                              # 配置文件层
│   ├── system.yaml                      #   系统全局配置
│   └── setting_manager.py               #   配置读写管理器（加载/校验/覆盖）
│
├── engine/                              # 引擎层（业务流程编排）
│   ├── recorder_engine.py              #   录制引擎核心（F2/F3 状态机调度）
│   ├── step_builder.py                  #   步骤构造器（由感知数据 → 标准化步骤对象）
│   ├── pipeline_runner.py               #   (空壳) 外环调度器，预留回放
│   └── hotkey_registry.py               #   全局热键注册与分发
│
├── core/                                # 核心业务模块（接口+实现）
│   ├── perception_provider.py           #   感知模块：截图/鼠标/窗口/DPI
│   ├── locator_protocol.py              #   BaseLocator 抽象接口 + 工厂
│   ├── locators/                        #   定位器实现集合
│   │   ├── __init__.py
│   │   ├── fixed_locator.py             #   固定坐标定位器
│   │   ├── template_locator.py          #   模板匹配定位器
│   │   └── llm_locator.py               #   (占位) LLM定位器，不实现
│   ├── action_executor.py               #   (空壳) 动作执行器
│   └── change_validator.py              #   (空壳) 界面变化验证器
│
├── data/                                # 数据层（运行时产出）
│   ├── workflow_schema.json              #   workflow.json 的 schema 定义
│   ├── workdir/                          #   工作流数据目录
│   │   ├── workflow.json                #   当前录制的步骤配置
│   │   ├── templates/                   #   F3框选截取的模板PNG
│   │   └── snapshots/                   #   (预留) 录制过程全屏快照备份
│   └── data_manager.py                  #   数据读写管理器（路径解析/文件IO/目录初始化）
│
├── utils/                               # 工具层（无业务语义）
│   ├── dpi_calculator.py                #   DPI获取与坐标换算工具
│   ├── image_entropy_calculator.py      #   (预留)图像信息熵计算
│   ├── hash_calculator.py               #   (预留)dHash指纹计算
│   └── logger_setup.py                  #   日志初始化工具
│
└── logs/                                # 日志目录
    └── recorder.log                     #   录制过程日志
```

### 命名规范说明

| 层级 | 包名 | 后缀约定 | 示例 |
| :--- | :--- | :--- | :--- |
| 配置文件层 | `config/` | `_manager` | `config_manager.py` |
| 引擎层 | `engine/` | `_engine`, `_builder`, `_registry` | `recorder_engine.py` |
| 核心层 | `core/` | `_provider`, `_protocol`, `_executor`, `_validator` | `perception_provider.py` |
| 核心子包 | `core/locators/` | `_locator` | `fixed_locator.py` |
| 数据层 | `data/` | `_manager` | `data_manager.py` |
| 工具层 | `utils/` | `_calculator`, `_setup` | `dpi_calculator.py` |

### 层次依赖规则

```text
main.py
  └── engine/ (业务流程)
        ├── config/ (配置)
        ├── core/ (业务接口+实现)
        └── data/ (数据读写)
              └── utils/ (无业务工具)
```

依赖方向**严格单向**：入口 → 引擎 → 核心 + 配置 + 数据 → 工具。下层不能引用上层。

---

## 九、LLM接入路径（远期参考）

当需要从固定点击升级为语义理解点击时：

1. **实现 `LLMLocator`**：继承 `BaseLocator`，在 `locate()` 中实现截屏→转Base64→构造Prompt→调用多模态API→解析返回坐标
2. **修改 1 处代码**：
   - 录制时：`method` 字段设为 `"llm"`，`norm_x/norm_y` 可留空
   - 回放时：工厂创建 `LLMLocator` 实例
3. **上下游零修改**：Perception 仍负责截图，Action 仍负责执行，Validator 仍负责 dHash 预检

也可在**录制阶段**用 LLM 辅助定位：

- F2 触发后，将截图+鼠标位置发送给 LLM，让 LLM 确认目标元素并返回精确锚点区域
- 这时 Locator 录制端用 LLM 做"智能采集"，数据格式仍是标准的 `workflow.json`

---

## 十、当前开发步骤

1. **第一阶段**：搭建完整项目骨架（所有文件+空壳类）
2. **第二阶段**：实现 `core/perception_provider.py`（截图/鼠标/窗口/DPI）
3. **第三阶段**：实现 `engine/recorder_engine.py`（F2/F3状态机）+ `engine/step_builder.py`
4. **第四阶段**：实现 `main.py` + `engine/hotkey_registry.py`（全局热键注册）
5. **第五阶段**：实现 `data/data_manager.py` + `core/locator_protocol.py` + `FixedLocator`
6. **第六阶段**：集成测试与边界情况处理
