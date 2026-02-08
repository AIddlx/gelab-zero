# GELab-Zero Android GUI Agent Skill

GELab-Zero 是一个移动端 GUI Agent 系统，通过视觉理解自主控制 Android 设备。

## 核心能力

### 支持的操作

| 操作 | 说明 |
|------|------|
| CLICK/TAP | 点击屏幕 |
| TYPE | 输入文本 |
| SWIPE | 滑动 |
| BACK | 返回键 |
| HOME | 主页键 |
| PRESS_KEY | 系统按键 |
| WAIT | 等待 |

## 基本用法

```bash
python examples/run_single_task.py "任务描述"
```

### 示例

```bash
# 简单任务
python examples/run_single_task.py "打开计算器"

# 复杂任务
python examples/run_single_task.py "打开淘宝，搜索 iPhone，按销量排序"
```

## 前置要求（使用前请确保已完成安装）

### 必须已安装并运行：
1. **虚拟环境**：已创建并激活
2. **依赖包**：已在虚拟环境中安装
3. **Ollama 模型**：已下载并运行 `ollama run gelab-zero-4b-preview`
4. **Android 设备**：已启用 USB 调试并连接

### 在虚拟环境中启动：

**Windows PowerShell:**
```powershell
# 激活虚拟环境
ddlx\venv\Scripts\Activate.ps1

# 进入项目目录
cd gelab-zero

# 执行任务
python examples/run_single_task.py "任务描述"
```

**Windows CMD:**
```
ddlx\venv\Scripts\activate.bat
cd gelab-zero
python examples/run_single_task.py "任务描述"
```

**Linux/Mac:**
```bash
source ddlx/venv/bin/activate
cd gelab-zero
python examples/run_single_task.py "任务描述"
```

首次安装请参考：[SETUP_GUIDE.md](../docs/SETUP_GUIDE.md)

## MCP 服务

- **详细 MCP**（端口 8704）：完整任务执行
- **单步动作 MCP**（端口 8705）：单步控制

配置：[MCP_SERVER.md](../docs/MCP_SERVER.md)

## 输出

- 文本日志：`running_log/logs/run_single_task_*.log`
- 截图文件：`running_log/server_log/os-copilot-local-eval-logs/images/`

## 限制

- 只能控制 Android 设备
- 需要 GUI 界面
