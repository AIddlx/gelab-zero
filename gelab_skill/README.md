# GELab-Zero Skill for AI Agents

这个文件夹包含 GELab-Zero Android GUI Agent 的 skill 定义，让其他 AI（如 Claude、ChatGPT）能够理解并调用 `run_single_task.py`。

## 文件说明

| 文件 | 用途 |
|------|------|
| `skill.md` | **核心 skill 定义** - AI 阅读后理解如何使用 GELab-Zero |
| `examples.md` | 使用示例 - 常见任务的执行示例 |
| `api_reference.md` | API 参考 - 参数和配置详解 |

## 快速开始

1. AI 阅读 `skill.md` 了解能力
2. 使用以下命令调用：

```bash
python examples/run_single_task.py "任务描述"
```

## 示例

```bash
# 打开计算器
python examples/run_single_task.py "打开计算器"

# 淘宝购物
python examples/run_single_task.py "去淘宝帮我买本 Python 书"

# 微信操作
python examples/run_single_task.py "打开微信，搜索文件传输助手"
```

## 注意事项

- 需要 Android 设备通过 ADB 连接
- 需要本地 LLM（Ollama/vLLM）运行
- 首次使用会自动配置无线连接
