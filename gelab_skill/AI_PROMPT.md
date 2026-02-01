# GELab-Zero AI Prompt

> 给 AI Agent 的快速参考提示

## 你现在可以使用 GELab-Zero Android GUI Agent

### 核心能力

你可以通过自然语言让 Android 设备自动执行操作：
- 点击、滑动、输入文本
- 打开应用、导航界面
- 完成复杂的多步骤任务

### 调用命令

```bash
cd C:\Project\IDEA\2\gelab-zero
python examples/run_single_task.py "任务描述"
```

### 示例命令

```bash
# 基础操作
python examples/run_single_task.py "打开计算器"
python examples/run_single_task.py "打开微信"
python examples/run_single_task.py "返回桌面"

# 复杂任务
python examples/run_single_task.py "打开淘宝，搜索 iPhone，查看第一个商品"
python examples/run_single_task.py "打开微信，找到张三，发送消息你好"

# 导航操作
python examples/run_single_task.py "下滑页面"
python examples/run_single_task.py "点击返回按钮"
python examples/run_single_task.py "长按屏幕中央"
```

### 支持的操作

| 操作 | 说明 |
|------|------|
| CLICK | 点击屏幕上的位置 |
| TYPE | 输入文本（支持中文） |
| SWIPE/SCROLL | 滑动屏幕 |
| LONGPRESS | 长按 |
| BACK/HOME | 系统按键 |
| AWAKE | 启动应用 |
| WAIT | 等待 |
| COMPLETE | 完成任务 |

### 输出解读

```
Step 1/400 (2.3s) - CLICK (500.00, 300.00) "计算器"
  📸 截图: running_log/.../session_123_step_1.jpeg
```

- `Step 1/400`: 第 1 步，共最多 400 步
- `2.3s`: 本步耗时
- `CLICK (500, 300)`: 点击坐标 (500, 300)
- `📸 截图`: 本步截图保存路径

### 前置要求

1. **Android 设备** 已通过 ADB 连接
2. **Ollama** 正在运行 gelab-zero-4b-preview 模型
3. **Python** 依赖已安装

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| 无设备 | 检查 ADB 连接 |
| 无法连接模型 | 确认 Ollama 运行中 |
| 任务失败 | 简化任务描述 |

### 完整文档

详细文档请参考：
- `skill.md` - 完整 skill 定义
- `examples.md` - 使用示例
- `api_reference.md` - API 参考
