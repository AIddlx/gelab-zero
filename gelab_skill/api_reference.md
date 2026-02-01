# GELab-Zero API 参考

本文档详细说明 `run_single_task.py` 的参数、配置和输出格式。

## 命令行 API

### 基本语法

```bash
python examples/run_single_task.py <任务描述> [选项]
```

### 参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| 任务描述 | string | ✅ | - | 要执行的任务的自然语言描述 |

### 示例

```bash
# 最简单调用
python examples/run_single_task.py "打开计算器"

# 复杂任务
python examples/run_single_task.py "打开淘宝，搜索iPhone，按销量排序，查看第一个商品的详情"
```

## 配置 API

### 模型配置

位置：`examples/run_single_task.py` 第 99-121 行

```python
local_model_config = {
    # 解析器类型
    "task_type": "parser_0922_summary",

    # 模型配置
    "model_config": {
        "model_name": "gelab-zero-4b-preview",  # 模型名称
        "model_provider": "local",              # 提供商: local 或 openai
        "args": {
            "temperature": 0.1,       # 温度参数 (0.0-1.0)
            "top_p": 0.95,           # Top-p 采样
            "frequency_penalty": 0.0, # 频率惩罚
            "max_tokens": 4096,      # 最大 token 数
        },
    },

    # 执行配置
    "max_steps": 400,            # 最大执行步数
    "delay_after_capture": 2,    # 截图后等待时间（秒）
    "debug": False              # 调试模式
}
```

### 配置项详解

#### task_type

| 值 | 说明 |
|-----|------|
| `parser_0922_summary` | 标准解析器，支持所有操作类型 |

#### model_provider

| 值 | 说明 | 要求 |
|-----|------|------|
| `local` | 本地 Ollama/vLLM | 需要本地运行 LLM |
| `openai` | OpenAI API | 需要 API Key |

#### temperature

- **范围**: 0.0 - 1.0
- **说明**: 控制输出的随机性
- **推荐**:
  - `0.0-0.2`: 精确操作（推荐）
  - `0.3-0.5`: 平衡模式
  - `0.6-1.0**: 创造性模式

#### max_steps

- **类型**: integer
- **默认**: 400
- **说明**: 任务执行的最大步数
- **推荐**: 根据任务复杂度调整
  - 简单任务: 50-100
  - 中等任务: 100-200
  - 复杂任务: 200-400

#### delay_after_capture

- **类型**: float (秒)
- **默认**: 2.0
- **说明**: 截图后等待页面加载的时间
- **推荐**:
  - 快速网络: 1.0-1.5
  - 正常网络: 2.0-3.0
  - 慢速网络: 3.0-5.0

## 输出格式

### 控制台输出

#### 正常输出

```
Step {step}/{max_steps} ({time}s) - {action_type} {params}
  📸 截图: {screenshot_path}
  说明: {action_explain}
```

#### 输出元素

| 元素 | 说明 |
|------|------|
| step | 当前步骤号 |
| max_steps | 最大步数 |
| time | 本步耗时（秒） |
| action_type | 操作类型 |
| params | 操作参数 |
| screenshot_path | 截图文件路径 |

### 操作类型格式

| 类型 | 格式 | 示例 |
|------|------|------|
| CLICK | `CLICK (x, y) "标签"` | `CLICK (500.00, 300.00) "计算器"` |
| TYPE | `TYPE "文本内容"` | `TYPE "Hello World"` |
| SWIPE | `SWIPE 方向` 或 `SWIPE (x1,y1)→(x2,y2)` | `SWIPE up` |
| SCROLL | `SCROLL 方向` | `SCROLL down` |
| LONGPRESS | `LONGPRESS (x, y)` | `LONGPRESS (500.00, 300.00)` |
| BACK | `BACK` | `BACK` |
| HOME | `HOME` | `HOME` |
| HOT_KEY | `HOT_KEY 按键名` | `HOT_KEY volume_up` |
| AWAKE | `AWAKE "应用名"` | `AWAKE "微信"` |
| WAIT | `WAIT 时间s` | `WAIT 2s` |
| COMPLETE | `COMPLETE "原因"` | `COMPLETE "任务完成"` |
| INFO | `INFO "问题"` | `INFO "请确认是否继续"` |

### 日志文件格式

#### 主日志文件

**位置**: `running_log/logs/run_single_task_YYYYMMDD_HHMMSS.log`

**格式**:
```
2026-01-31 21:00:00 - __main__ - INFO - 程序启动
2026-01-31 21:00:01 - __main__ - INFO - 任务描述: 打开计算器
2026-01-31 21:00:02 - __main__ - DEBUG - ====== Step 1 开始 ======
2026-01-31 21:00:03 - __main__ - DEBUG - Payload: {...}
2026-01-31 21:00:04 - __main__ - DEBUG - Result: {...}
2026-01-31 21:00:05 - __main__ - DEBUG - Step 1 耗时: 2.34 秒
```

#### 轨迹文件 (JSONL)

**位置**: `running_log/server_log/os-copilot-local-eval-logs/traces/*.jsonl`

**格式** (每行一个 JSON):
```json
{
  "session_id": "abc123",
  "step": 1,
  "timestamp": "2026-01-31T21:00:00",
  "action": {
    "action_type": "CLICK",
    "point": {"x": 500, "y": 300},
    "label": "计算器"
  },
  "screenshot": "images/abc123_step_1.jpeg"
}
```

## 错误码

### 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|----------|
| `错误：未传入任务参数！` | 缺少任务描述 | 添加任务描述参数 |
| `未检测到已连接设备` | ADB 未连接 | 连接 Android 设备 |
| `无法连接到 Ollama` | LLM 服务未运行 | 启动 Ollama 服务 |
| `任务执行失败` | 任务无法完成 | 简化任务描述 |

### 错误处理

脚本遇到错误时会：
1. 在控制台显示错误信息
2. 记录详细错误到日志文件
3. 清理连接并退出

## 性能参数

### 延迟参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| delay_after_capture | 2.0s | 截图后等待 |
| max_steps | 400 | 最大步数 |

### 资源占用

| 资源 | 典型值 |
|------|--------|
| 内存 | 500MB - 2GB |
| CPU | 10% - 30% |
| 网络 | 取决于视频流 |

## 扩展配置

### 自定义日志级别

修改 `setup_logging()` 函数：

```python
# 控制台只显示 ERROR
console_handler.setLevel(logging.ERROR)

# 文件记录所有级别
file_handler.setLevel(logging.DEBUG)
```

### 禁用视频窗口

确保配置中 `show_window=False` (默认)

### 启用调试模式

```python
local_model_config = {
    "debug": True,  # 启用调试模式
}
```

## 高级用法

### 编程调用

可以在 Python 脚本中直接调用：

```python
from copilot_agent_client.pu_client import evaluate_task_on_device

result = evaluate_task_on_device(
    task="打开计算器",
    device_id="emulator-5554",
    max_steps=100
)
```

### 批量任务

创建任务列表并批量执行：

```python
tasks = [
    "打开计算器",
    "打开设置",
    "打开微信"
]

for task in tasks:
    print(f"执行任务: {task}")
    # 调用 run_single_task.py
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PYTHONPATH` | Python 模块搜索路径 | 当前目录 |
| `OLLAMA_HOST` | Ollama 服务地址 | `http://localhost:11434` |
| `ADB_SERVER` | ADB 服务地址 | `localhost:5037` |

## 版本兼容性

| 组件 | 版本要求 |
|------|----------|
| Python | 3.12+ |
| Ollama | Latest |
| Android | 7.0+ (API 24+) |
| ADB | Latest |
