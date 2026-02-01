# MCP 服务器

gelab-zero 提供 MCP (Model Context Protocol) 服务器支持，实现多设备管理和任务分发。

---

## 快速开始

### 启动服务器

```bash
# 详细版（推荐）
python mcp_server/detailed_gelab_mcp_server.py

# 简化版
python mcp_server/simple_gelab_mcp_server.py
```

服务器默认运行在 `http://localhost:8704`

---

## MCP 工具

| 工具 | 功能 | 参数 |
|------|------|------|
| `ask_agent` | 执行 GUI 任务 | `task`, `max_steps`, `reset_environment` |
| `list_devices` | 列出设备 | - |
| `get_device_info` | 获取设备信息 | `device_id` |
| `screenshot` | 截图 | `device_id`, `filename` |

---

## 使用方式

### Python 客户端

```python
from fastmcp import Client
import asyncio

async def main():
    async with Client("http://localhost:8704/mcp") as client:
        # 列出设备
        devices = await client.call_tool("list_devices", {})
        print("设备列表:", devices)

        # 执行任务
        result = await client.call_tool(
            "ask_agent",
            {
                "task": "打开计算器",
                "max_steps": 100,
                "reset_environment": False
            }
        )
        print("执行结果:", result)

asyncio.run(main())
```

### Chatbox 集成

1. 启动 MCP 服务器
2. Chatbox 设置 → MCP → 添加服务器
3. 输入地址：`http://localhost:8704/mcp`
4. 开始对话

---

## 配置

配置文件：`mcp_server_config.yaml`

```yaml
server_config : {
    "mcp_server_port": 8704,          # 服务器端口
    "log_dir": "running_log/...",     # 日志目录
    "image_dir": "running_log/...",   # 截图目录
    "debug": False,

    # 任务超时配置
    "default_task_timeout": 600,      # 默认 10 分钟
    "max_task_timeout": 1800,         # 最大 30 分钟
}
```

---

## HTTP MCP 服务器（新增）

**本版本新增** HTTP 模式 MCP 服务器，支持远程调用。

### 启动 HTTP 服务器

```bash
python mcp_server/simple_http_mcp_server.py
```

### 调用示例

```bash
curl -X POST http://localhost:8704/mcp/tools/ask_agent \
  -H "Content-Type: application/json" \
  -d '{
    "task": "打开设置",
    "max_steps": 50
  }'
```

---

## stdio 包装器（新增）

**本版本新增** stdio 模式支持，适合本地集成。

```bash
python mcp_server/stdio_wrapper.py
```

适用于 Claude Code、Cline 等 MCP 客户端。

---

## 架构

```
┌─────────────┐     MCP Protocol     ┌──────────────┐
│   MCP 客户端 │ ←──────────────────→ │ MCP 服务器   │
│  (Chatbox)  │                       │ (port 8704)  │
└─────────────┘                       └──────────────┘
                                             │
                                             ▼
                                    ┌──────────────┐
                                    │ GUI Agent    │
                                    │ (gelab-zero)  │
                                    └──────────────┘
                                             │
                        ┌────────────────────┼────────────────────┐
                        ▼                    ▼                    ▼
                   ┌─────────┐         ┌─────────┐         ┌─────────┐
                   │ 设备 1   │         │ 设备 2   │         │ 设备 N   │
                   └─────────┘         └─────────┘         └─────────┘
```

---

## 批处理脚本

### Windows

```batch
# 启动 HTTP 服务器
mcp_server/start_http.bat

# 启动 stdio 服务器
mcp_server/start_stdio.bat
```

---

## 故障排除

### 服务器无法启动

1. 检查端口占用：`netstat -ano | findstr 8704`
2. 确认依赖安装：`pip install fastmcp mcp`
3. 查看日志输出

### 工具调用失败

1. 确认设备已连接：`adb devices`
2. 检查 MCP 配置文件
3. 查看 gelab-zero 日志

---

## 配置 Claude Code

在 Claude Code 设置中添加 MCP 服务器：

```json
{
  "mcpServers": {
    "gelab-zero": {
      "command": "python",
      "args": ["mcp_server/stdio_wrapper.py"],
      "cwd": "/path/to/gelab-zero"
    }
  }
}
```

---

## 相关文档

- [MCP 协议规范](https://modelcontextprotocol.io/)
- [fastmcp 文档](https://github.com/jlowin/fastmcp)
