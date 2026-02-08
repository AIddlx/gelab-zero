# GELab-Zero 使用步骤

## 前置要求

- Python 3.12+
- Android 设备（已开启 USB 调试）
- ADB 工具已安装
- Ollama（本地 LLM 推理）
- **scrcpy-py-ddlx**（gelab-zero 的必需依赖，将在步骤 1 中克隆）

---

## 步骤 0: 创建虚拟环境

```bash
# 创建 ddlx 目录
mkdir ddlx

# 创建虚拟环境
python -m venv ddlx/venv

# 激活虚拟环境

# Windows PowerShell:
ddlx/venv/Scripts/Activate.ps1

# Windows CMD:
ddlx/venv/Scripts/activate.bat

# Linux/Mac:
source ddlx/venv/bin/activate
```

激活成功后，命令行前面会显示 `(venv)` 提示符。

**如果 PowerShell 遇到执行策略错误：**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 步骤 1: 克隆项目

**注意**: gelab-zero 依赖于 scrcpy-py-ddlx，两个项目必须放在**同级目录**。

```bash
# 先进入 ddlx 工作目录（或创建后进入）
cd ddlx

# 克隆 scrcpy-py-ddlx（必需依赖）
git clone https://github.com/AIddlx/scrcpy-py-ddlx

# 克隆 gelab-zero（主项目）
git clone https://github.com/AIddlx/gelab-zero

# 进入 gelab-zero 目录
cd gelab-zero
```

**目录结构要求**:
```
ddlx/
├── venv/                     # 虚拟环境（步骤 0 创建）
├── scrcpy-py-ddlx/           # 必需！与 gelab-zero 同级
└── gelab-zero/               # 主项目
```

---

## 步骤 2: 安装依赖

```bash
pip install -r requirements.txt
```

---

## 步骤 3: 下载模型

### 方式 1: 魔搭 ModelScope（推荐）

```bash
pip install modelscope
# 使用 modelscope 下载模型
```

### 方式 2: Hugging Face

```bash
pip install huggingface_hub

# 国内加速
# Windows:
$env:HF_ENDPOINT = "https://hf-mirror.com"
# Linux/Mac:
export HF_ENDPOINT="https://hf-mirror.com"

# 下载模型
hf download stepfun-ai/GELab-Zero-4B-preview --local-dir gelab-zero-4b-preview
```

---

## 步骤 4: 模型部署

```bash
cd gelab-zero-4b-preview

# 导入 Ollama
ollama create gelab-zero-4b-preview -f Modelfile

# 启动模型服务（必须）
ollama run gelab-zero-4b-preview
```

确保 Ollama 模型服务正常运行后，再进行后续步骤。

---

## 步骤 5: 连接设备

插上 USB 线，拔插一次让电脑识别设备。

---

## 步骤 6: 运行任务

### 单任务脚本

```bash
python examples/run_single_task.py "打开计算器"
```

首次运行会自动启用无线 ADB，之后可拔线使用。

### MCP 服务器

```bash
python mcp_server/detailed_gelab_mcp_server.py
```

服务器运行在 `http://localhost:8704`，可在 Chatbox 或 Claude Code 中配置使用。

---

## 输出位置

| 类型 | 路径 |
|------|------|
| 文本日志 | `running_log/logs/run_single_task_*.log` |
| 轨迹日志 | `running_log/server_log/os-copilot-local-eval-logs/traces/*.jsonl` |
| 截图 | `running_log/server_log/os-copilot-local-eval-logs/images/` |

---
