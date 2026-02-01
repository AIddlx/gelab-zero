"""
简单 HTTP MCP 服务器
不依赖 FastMCP 的 SSE 流式传输，直接使用标准 HTTP POST/JSON-RPC
"""

import sys
if "." not in sys.path:
    sys.path.append(".")

import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

# 配置日志
log_dir = Path("running_log/mcp_server")
log_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now()
log_file = log_dir / f"simple_http_mcp_{timestamp.strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 70)
logger.info("简单 HTTP MCP 服务器启动")
logger.info(f"日志文件: {log_file}")
logger.info("=" * 70)

# 导入后端实现
from copilot_front_end.mobile_action_helper import list_devices
from mcp_server.mcp_backend_implements import execute_task

# MCP 协议版本和服务器信息
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "gelab-mcp-server",
    "version": "1.0.0",
    "protocolVersion": MCP_PROTOCOL_VERSION
}

# 定义工具列表
TOOLS = [
    {
        "name": "list_connected_devices",
        "description": "列出所有连接的移动设备",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "ask_agent",
        "description": """# GUI Agent Documentation

让 GUI Agent 在连接的设备上执行指定任务。
GUI Agent 可以理解自然语言指令并相应地与设备交互。
Agent 可以执行高级任务描述。

## Agent 的能力限制：

1. 任务必须与设备上已安装的应用相关。例如："打开微信，帮张三发一条消息，说今天下午三点开会"；"帮我在淘宝上搜索一款性价比高的手机，并加入购物车"。

2. 任务必须简单具体。例如："在 xxx 应用中做 yyy"；"在 xxx 应用中查找 xxx 信息"。一次只在一个应用上做一个任务。

3. Agent 可能无法处理需要多步推理或规划的复杂任务。您需要将复杂任务分解为更简单的子任务，然后让 Agent 顺序执行。

4. Agent 不能接受多模态输入。如果您想提供额外的信息（如截图说明），请将其包含在任务描述中。

## 使用指导：

1. 您永远不应该直接要求 Agent 付款或订购任何东西。如果用户想要购买，您应该在订购/付款前让 Agent 停止，让用户自己订购/付款。

2. 告诉 Agent，如果在任务执行过程中出现人工验证，Agent 应该询问 Client。当您看到 INFO 时，您应该要求用户手动处理验证。用户说"完成"后，您可以使用 session_id 和 device_id 继续任务，并在 reply_from_client 中要求 Agent 继续。

返回：
    dict: 包含任务执行详情的执行日志。
""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "要执行任务的设备 ID，由 list_connected_devices 工具列出。"
                },
                "task": {
                    "type": "string",
                    "description": "Agent 需要在移动设备上执行的任务。如果这不是 None，Agent 将尝试执行此任务。如果是 None，则必须提供 session_id 以继续上一个会话。"
                },
                "max_steps": {
                    "type": "integer",
                    "description": "Agent 完成任务可以执行的最大步数。",
                    "default": 20
                },
                "session_id": {
                    "type": "string",
                    "description": "可选，上一个任务以 INFO 操作结束时必须提供 session ID，此时需要回复，必须提供 session id 和 device id 以及来自 client 的回复。"
                },
                "reply_from_client": {
                    "type": "string",
                    "description": "如果上一个任务以 INFO 操作结束，您想给 GUI Agent 一个回复，请在这里提供回复。如果是这样，您必须提供上一个 session id 和上一个 device id。"
                }
            },
            "required": ["device_id"]
        }
    }
]

# 服务器资源列表
RESOURCES = []

# 提示词列表
PROMPTS = []


async def handle_mcp_request(request: Request) -> JSONResponse:
    """处理 MCP JSON-RPC 请求"""
    try:
        body = await request.json()
        logger.debug(f"收到请求: {json.dumps(body, ensure_ascii=False)[:200]}")

        request_method = body.get("method")
        request_id = body.get("id")
        params = body.get("params", {})

        if request_method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": SERVER_INFO,
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    }
                }
            }
        elif request_method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": TOOLS
                }
            }
        elif request_method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name == "list_connected_devices":
                result = list_devices()
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False)
                            }
                        ]
                    }
                }
            elif tool_name == "ask_agent":
                # 调用后端执行任务
                device_id = tool_args.get("device_id")
                task = tool_args.get("task")
                max_steps = tool_args.get("max_steps", 20)
                session_id = tool_args.get("session_id")
                reply_from_client = tool_args.get("reply_from_client")

                result = execute_task(
                    device_id=device_id,
                    task=task,
                    reset_environment=(task is not None),
                    max_steps=max_steps,
                    enable_intermediate_logs=False,
                    enable_intermediate_image_caption=False,
                    enable_intermediate_screenshots=False,
                    enable_final_screenshot=True,
                    enable_final_image_caption=False,
                    reply_mode="no_reply",  # HTTP 模式下不使用 INFO 回复
                    session_id=session_id,
                    reply_from_client=reply_from_client,
                    extra_info={}
                )

                # 格式化返回结果
                result_text = json.dumps(result, ensure_ascii=False, indent=2)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result_text
                            }
                        ]
                    }
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        elif request_method == "resources/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resources": RESOURCES
                }
            }
        elif request_method == "prompts/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "prompts": PROMPTS
                }
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {request_method}"
                }
            }

        logger.debug(f"响应: {json.dumps(response, ensure_ascii=False)[:200]}")
        return JSONResponse(response)

    except Exception as e:
        logger.exception("处理请求时出错")
        response = {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return JSONResponse(response, status_code=500)


async def health_check(request: Request) -> JSONResponse:
    """健康检查端点"""
    devices = list_devices()
    return JSONResponse({
        "status": "healthy",
        "service": "gelab-simple-http-mcp-server",
        "devices": len(devices),
        "device_list": devices
    })


# 定义路由
routes = [
    Route("/mcp", handle_mcp_request, methods=["POST"]),
    Route("/health", health_check, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)


if __name__ == "__main__":
    import yaml

    with open("mcp_server_config.yaml", "r", encoding="utf-8") as f:
        mcp_server_config = yaml.safe_load(f)

    port = mcp_server_config['server_config'].get("mcp_server_port", 8704)

    logger.info("=" * 70)
    logger.info(f"启动简单 HTTP MCP 服务器")
    logger.info(f"端口: {port}")
    logger.info(f"MCP 端点: http://127.0.0.1:{port}/mcp")
    logger.info(f"健康检查: http://127.0.0.1:{port}/health")
    logger.info("=" * 70)

    print("")
    print("=" * 70)
    print("[启动] 简单 HTTP MCP 服务器")
    print("[模式] 标准 HTTP POST (无 SSE，无会话)")
    print(f"[端点] MCP: http://127.0.0.1:{port}/mcp")
    print(f"[健康检查] http://127.0.0.1:{port}/health")
    print("=" * 70)
    print("")

    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
