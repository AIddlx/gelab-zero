# GELab-Zero Android GUI Agent Skill

> 复制以下内容给 AI，让它了解如何使用 GELab-Zero

---

**name:** gelab-zero
**description:** "Android GUI automation agent that controls devices through natural language. When you need to automate Android device tasks for: (1) Opening apps and navigating UI, (2) Clicking, typing, swiping on screen, (3) Completing multi-step tasks, (4) Reading screen content and taking screenshots. Always read skill.md first for complete guidance."

---

## 核心功能

通过自然语言描述任务，自动控制 Android 设备执行操作。

### 调用命令

```bash
cd C:\Project\IDEA\2\gelab-zero
python examples/run_single_task.py "任务描述"
```

### 支持的操作

- **CLICK** - 点击屏幕
- **TYPE** - 输入文本（支持中文）
- **SWIPE/SCROLL** - 滑动
- **LONGPRESS** - 长按
- **BACK/HOME** - 系统按键
- **AWAKE** - 启动应用

### 使用示例

```bash
# 基础操作
python examples/run_single_task.py "打开计算器"
python examples/run_single_task.py "打开微信"
python examples/run_single_task.py "返回桌面"

# 复杂任务
python examples/run_single_task.py "打开淘宝，搜索 iPhone，按销量排序"
python examples/run_single_task.py "打开微信，找到张三，发送消息你好"
```

### 前置要求

1. Android 设备已通过 ADB 连接
2. Ollama 正在运行 `gelab-zero-4b-preview` 模型
3. Python 依赖已安装

### 重要提示

**当需要使用 GELab-Zero 时，请先阅读 skill.md 全部内容，并基于 skill.md 的指引查看其余文件（examples.md、api_reference.md）**

---

## 文档索引

| 文件 | 说明 |
|------|------|
| `skill.md` | **核心技能定义**（必读） |
| `examples.md` | 使用示例 |
| `api_reference.md` | API 参数说明 |
| `USE_THIS_PROMPT.md` | 本文件（快速参考） |

---

**现在你可以帮我使用 GELab-Zero 执行 Android 任务了！**
