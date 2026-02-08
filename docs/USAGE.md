# 使用指南

## 快速开始

### 执行单个任务

```bash
python examples/run_single_task.py "打开计算器"
```

### 交互式对话模式

```bash
python examples/run_interactive.py
```

支持命令：
- `/quit` - 退出
- `/clear` - 清屏
- `/devices` - 列出设备

---

## run_single_task.py 详细说明

### 功能特点

1. **自动设备连接**
   - 自动检测 USB 设备
   - 自动启用无线模式
   - 局域网扫描发现设备

2. **实时预览窗口**
   - 显示设备屏幕
   - 记录每步耗时
   - 显示截图保存位置

3. **日志记录**
   - 文本日志：`running_log/logs/run_single_task_*.log`
   - 轨迹日志：`running_log/server_log/os-copilot-local-eval-logs/traces/*.jsonl`
   - 截图保存：`running_log/server_log/os-copilot-local-eval-logs/images/`

### 命令行参数

```
python examples/run_single_task.py "任务描述"
```

### 输出说明

执行过程中会显示：
```
▶ Step 1/400 (10.0s) - CLICK (448,19)
    说明: 点击搜索栏
    摘要: 激活搜索功能
  📸 截图: running_log/.../session_id_step_1.jpeg
```

- **Step X/400** - 当前步骤/最大步数
- **(10.0s)** - 本步耗时
- **CLICK** - 动作类型
- **📸 截图** - 截图文件路径

### 支持的动作类型

| 动作 | 说明 | 示例 |
|------|------|------|
| CLICK | 点击屏幕 | CLICK (500, 300) |
| TYPE | 输入文本 | TYPE "hello" |
| SWIPE | 滑动 | SWIPE (100,200) → (300,400) |
| LONGPRESS | 长按 | LONGPRESS (500, 300) |
| HOME | 返回主屏幕 | HOME |
| BACK | 返回键 | BACK |
| SCROLL | 滚动 | SCROLL down |
| WAIT | 等待 | WAIT 2s |
| COMPLETE | 任务完成 | COMPLETE "success" |

---

## 配置说明

### 模型配置

编辑 `examples/run_single_task.py` 中的 `local_model_config`：

```python
local_model_config = {
    "task_type": "parser_0922_summary",
    "model_config": {
        "model_name": "gelab-zero-4b-preview",  # 模型名称
        "model_provider": "local",               # 模型提供者
        "args": {
            "temperature": 0.1,
            "top_p": 0.95,
            "max_tokens": 4096,
        }
    },
    "max_steps": 400,           # 最大执行步数
    "delay_after_capture": 2,   # 截图后延迟
}
```

### 服务器配置

```python
tmp_server_config = {
    "log_dir": "running_log/server_log/os-copilot-local-eval-logs/traces",
    "image_dir": "running_log/server_log/os-copilot-local-eval-logs/images",
    "debug": False
}
```

---

## 常见问题

### Q: 如何连接设备？

**A:** 支持三种方式：

1. **USB 连接** - 用数据线连接手机和电脑
2. **自动启用无线** - 插上 USB 线运行，自动启用无线模式，然后可拔线
3. **无线连接** - 确保手机和电脑在同一 WiFi，程序会自动扫描并连接

### Q: 没有检测到设备怎么办？

**A:** 检查：
1. 手机是否开启 USB 调试
2. 是否已授权电脑调试
3. 是否安装了 ADB 工具

### Q: 如何查看执行过程中的截图？

**A:** 每步执行后会在控制台显示截图路径，例如：
```
📸 截图: running_log/server_log/os-copilot-local-eval-logs/images/20250131_123456_abcdef_step_1.jpeg
```

直接复制路径在文件管理器中打开即可。

### Q: 任务执行失败怎么办？

**A:** 查看：
1. 控制台错误信息
2. 日志文件：`running_log/logs/run_single_task_*.log`
3. 检查 LLM 是否正确响应（查看日志中的 model_response）
