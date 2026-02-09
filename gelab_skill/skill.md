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
1. **虚拟环境**：已创建
2. **依赖包**：已在虚拟环境中安装
3. **Ollama 模型**：已下载并运行 `ollama run gelab-zero-4b-preview`
4. **Android 设备**：已启用 USB 调试并连接

### 执行脚本的方式：

**方式1：直接使用虚拟环境 Python（AI/自动化推荐）**

这种方式不依赖虚拟环境激活，最可靠：

Windows PowerShell:
```powershell
Set-Location "C:\Project\IDEA\2\ddlx\gelab-zero"
& "C:\Project\IDEA\2\ddlx\venv\Scripts\python.exe" "examples\run_single_task.py" "任务描述"
```

Linux/Mac:
```bash
cd /path/to/ddlx/gelab-zero
/path/to/ddlx/venv/bin/python examples/run_single_task.py "任务描述"
```

**方式2：激活虚拟环境后执行（手动操作）**

Windows PowerShell（注意使用 `.` 而不是 `&`）:
```powershell
. "C:\Project\IDEA\2\ddlx\venv\Scripts\Activate.ps1"
cd C:\Project\IDEA\2\ddlx\gelab-zero
python examples\run_single_task.py "任务描述"
```

Windows CMD:
```cmd
C:\Project\IDEA\2\ddlx\venv\Scripts\activate.bat
cd C:\Project\IDEA\2\ddlx\gelab-zero
python examples\run_single_task.py "任务描述"
```

**重要提示：**
- PowerShell 中必须用 `. "...\Activate.ps1"`（dot source），不能用 `&`
- CMD 中使用 `activate.bat`
- 如果移动过项目目录，需要重建虚拟环境，详见 [虚拟环境故障排查](../docs/VENV_TROUBLESHOOTING.md)

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
