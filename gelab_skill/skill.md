# GELab-Zero Android GUI Agent Skill

> 给 AI Agent 阅读的 skill 定义文档

## 概述

GELab-Zero 是一个移动端 GUI Agent 系统，可以通过视觉理解自主控制 Android 设备。AI Agent 可以通过自然语言描述任务，GELab-Zero 会自动在 Android 设备上执行操作。

## 核心能力

### 支持的操作类型

| 操作类型 | 说明 | 示例 |
|---------|------|------|
| CLICK | 点击屏幕 | 点击按钮、图标 |
| TYPE | 输入文本 | 支持中文输入 |
| SWIPE | 滑动 | 上下滑动、翻页 |
| SCROLL | 滚动 | 快速滚动列表 |
| LONGPRESS | 长按 | 长按弹出菜单 |
| BACK | 返回键 | 返回上一页 |
| HOME | 主页键 | 返回桌面 |
| HOT_KEY | 系统按键 | 音量键、菜单键等 |
| AWAKE | 启动应用 | 通过应用名称启动 |
| WAIT | 等待 | 等待页面加载 |
| COMPLETE | 任务完成 | 标记任务完成 |
| INFO | 询问用户 | 需要用户输入时 |

### 技术架构

```
用户输入任务描述
       ↓
LLM 分析 + 视觉理解
       ↓
生成操作序列 (CLICK/TYPE/SWIPE...)
       ↓
scrcpy 执行操作 (快 5-10x)
       ↓
ADB 备用执行
```

## 调用方式

### 基本命令

```bash
python examples/run_single_task.py "任务描述"
```

### 完整路径

```bash
cd C:\Project\IDEA\2\gelab-zero
python examples/run_single_task.py "任务描述"
```

## 参数说明

### 位置参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| 任务描述 | string | ✅ | 自然语言描述要执行的任务 |

### 示例

```bash
# 简单任务
python examples/run_single_task.py "打开计算器"

# 复杂任务
python examples/run_single_task.py "去淘宝搜索 Python 编程入门书籍，按销量排序，查看第一本书的详情"

# 多步骤任务
python examples/run_single_task.py "打开微信，找到文件传输助手，发送消息Hello"
```

## 输入要求

### 环境要求

1. **Android 设备**
   - 已开启 USB 调试
   - 通过 ADB 连接到电脑
   - 或者已启用无线调试

2. **本地 LLM**
   - Ollama 运行 gelab-zero-4b-preview 模型
   - 或 vllm/llama.cpp 等兼容服务

3. **Python 环境**
   - Python 3.12+
   - 依赖包已安装 (`pip install -r requirements.txt`)

### 自动设备发现

如果没有检测到设备，脚本会：
1. 检查是否有 USB 设备连接
2. 自动启用 TCP/IP 无线模式 (`adb tcpip 5555`)
3. 获取设备 WiFi IP 地址
4. 建立无线连接

## 输出说明

### 控制台输出

```
Step 1/400 (2.3s) - CLICK (500.00, 300.00) "计算器"
  📸 截图: running_log/server_log/os-copilot-local-eval-logs/images/session_123_step_1.jpeg

Step 2/400 (1.8s) - TYPE "123"
  📸 截图: running_log/server_log/os-copilot-local-eval-logs/images/session_123_step_2.jpeg

✅ 任务完成！
```

### 日志文件

- **文本日志**: `running_log/logs/run_single_task_YYYYMMDD_HHMMSS.log`
- **轨迹文件**: `running_log/server_log/os-copilot-local-eval-logs/traces/*.jsonl`
- **截图文件**: `running_log/server_log/os-copilot-local-eval-logs/images/*.jpeg`

### 截图命名规则

```
{session_id}_step_{step_num}.jpeg
```

例如: `abc123_step_5.jpeg` 表示第 5 步的截图

## 配置说明

### 模型配置

默认使用 Ollama 本地模型，可在 `examples/run_single_task.py` 中修改：

```python
local_model_config = {
    "task_type": "parser_0922_summary",
    "model_config": {
        "model_name": "gelab-zero-4b-preview",  # 模型名称
        "model_provider": "local",              # local 或 openai
        "args": {
            "temperature": 0.1,
            "top_p": 0.95,
            "max_tokens": 4096,
        },
    },
    "max_steps": 400,           # 最大执行步数
    "delay_after_capture": 2,   # 截图后等待时间
}
```

### 视频窗口配置

默认不显示视频窗口。如需显示，修改代码添加：

```python
config = ClientConfig(
    show_window=True,  # 显示实时预览窗口
)
```

## 使用技巧

### 任务描述最佳实践

✅ **好的描述**：
- "打开淘宝，搜索 Python 书籍"
- "进入设置，关闭 WiFi"
- "打开微信，找到张三，发送消息"

❌ **不好的描述**：
- "做某事"（太模糊）
- "操作手机"（无具体目标）
- "帮我买东西"（缺少具体信息）

### 复杂任务拆分

对于复杂任务，可以分步执行：

```bash
# 步骤1: 打开应用
python examples/run_single_task.py "打开淘宝"

# 步骤2: 搜索商品
python examples/run_single_task.py "搜索 Python 编程入门书籍"

# 步骤3: 查看详情
python examples/run_single_task.py "点击第一个商品，查看详情页"
```

## 故障排除

### 问题：无法连接设备

**解决**：
1. 检查 USB 调试是否开启
2. 运行 `adb devices` 确认设备已连接
3. 尝试重新插拔 USB 线

### 问题：模型无法连接

**解决**：
1. 确认 Ollama 正在运行
2. 确认模型已加载：`ollama list`
3. 测试 API：`curl http://localhost:11434/api/generate`

### 问题：任务执行失败

**解决**：
1. 查看日志文件了解详细错误
2. 确认任务描述清晰明确
3. 尝试简化任务步骤

## 限制

- 只能控制 Android 设备
- 需要 GUI 界面（不支持纯命令行应用）
- 复杂任务可能需要多次尝试
- 某些应用可能需要特定权限

## 相关文档

- [完整使用指南](../docs/USAGE.md)
- [scrcpy 集成说明](../docs/SCRCPY_INTEGRATION.md)
- [项目架构文档](../ARCHITECTURE.md)
