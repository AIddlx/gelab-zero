"""
GELab MCP 服务器 - FastMCP 无状态 HTTP 模式

使用 FastMCP 框架，以无状态 HTTP 模式运行，最大兼容 MCP 客户端。
"""

import sys
import logging
import threading
from datetime import datetime
from pathlib import Path

# FastMCP 只显示 WARNING 及以上
from fastmcp import FastMCP, Context
from fastmcp.utilities.logging import configure_logging

if "." not in sys.path:
    sys.path.append(".")

from typing import Annotated, Optional
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.mcp_backend_implements import (
    get_device_list,
    execute_task,
)

# 配置日志
log_dir = Path("running_log/mcp_server")
log_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now()
log_file = log_dir / f"mcp_server_{timestamp.strftime('%Y%m%d_%H%M%S')}.log"

# 创建 logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 文件处理器 - 记录所有级别
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 控制台只显示 INFO 及以上
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

# 配置第三方库日志
configure_logging(level='WARNING')
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastmcp").setLevel(logging.WARNING)

logger.info("=" * 70)
logger.info("MCP 服务器日志系统初始化完成")
logger.info(f"日志文件: {log_file}")
logger.info("=" * 70)

# 创建 FastMCP 服务器
mcp = FastMCP(name="Gelab-MCP-Server", instructions="""
This MCP server provides tools to interact with connected mobile devices using a GUI agent.
""")


@mcp.tool
def list_connected_devices() -> list:
    """
    List all connected mobile devices.

    Returns:
        list: A list of connected device IDs.
    """
    devices = get_device_list()
    logger.info(f"连接的设备: {devices}")
    return devices


@mcp.tool
async def ask_agent(
    ctx: Context,
    device_id: Annotated[str, Field(description="ID of the device to perform the task on.")],
    task: Annotated[Optional[str], Field(description="The task description for the agent.")],
    max_steps: Annotated[int, Field(description="Maximum number of steps.")] = 20,
    session_id: Annotated[Optional[str], Field(description="Session ID for continuing previous task.")] = None,
    reply_from_client: Annotated[Optional[str], Field(description="Reply from client for INFO action.")] = None,
) -> dict:
    """
    Execute a GUI Agent task on the specified mobile device.

    The agent can understand natural language instructions and interact with the device.

    Args:
        device_id: Device ID from list_connected_devices
        task: Task description (e.g., "Open WeChat and send a message")
        max_steps: Maximum steps to complete the task
        session_id: Session ID to continue from a previous INFO action
        reply_from_client: Reply if the previous task ended with INFO action

    Returns:
        dict: Execution log with details including stop_reason, step counts, etc.
    """
    import asyncio

    reply_mode = "pass_to_client"
    cancel_event = threading.Event()

    logger.info(f"ask_agent() 调用 - device_id: {device_id}, task: {task}, max_steps: {max_steps}")

    # 发送开始消息（在无状态下可能不显示，但不影响执行）
    try:
        await ctx.info(f"任务: {task}")
        await ctx.info(f"设备: {device_id}")
    except Exception:
        pass  # 无状态下可能无法发送，忽略错误

    # 确定环境重置
    if task is not None:
        reset_environment = True
        session_id = None
    else:
        reset_environment = False
        if session_id is None:
            return {"error": "session_id is required when task is None"}

    # 进度回调（无状态模式下简化）
    def progress_callback(step_num, action_info, total_steps):
        """简化版进度回调 - 无状态模式下不发送实时进度"""
        if cancel_event.is_set():
            raise RuntimeError("Task cancelled")
        # 只记录日志，不发送进度
        action_type = action_info.get("action_type", "UNKNOWN")
        logger.debug(f"步骤 {step_num}/{total_steps}: {action_type}")

    # 执行任务
    try:
        loop = asyncio.get_event_loop()
        return_log = await loop.run_in_executor(
            None,
            lambda: execute_task(
                device_id=device_id,
                task=task,
                reset_environment=reset_environment,
                max_steps=max_steps,
                enable_intermediate_logs=False,
                enable_intermediate_image_caption=False,
                enable_intermediate_screenshots=False,
                enable_final_screenshot=False,
                enable_final_image_caption=False,
                reply_mode=reply_mode,
                session_id=session_id,
                reply_from_client=reply_from_client,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
        )
    except RuntimeError as e:
        if "cancelled" in str(e).lower():
            logger.info("[任务取消] 客户端中断了任务")
            return {
                "stop_reason": "CANCELLED_BY_CLIENT",
                "global_step_idx": 0,
                "error": "Task was cancelled by the client"
            }
        raise

    # 发送完成消息
    stop_reason = return_log.get("stop_reason", "UNKNOWN")
    total_steps = return_log.get("global_step_idx", 0)

    try:
        await ctx.info(f"执行完成 - 共{total_steps}步 - {stop_reason}")
    except Exception:
        pass

    return return_log


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """健康检查端点"""
    devices = get_device_list()
    return JSONResponse({
        "status": "healthy",
        "service": "gelab-mcp-server",
        "mode": "stateless_http",
        "devices": len(devices),
        "device_list": devices
    })


# 主程序入口
if __name__ == "__main__":
    import yaml

    # 加载配置
    with open("mcp_server_config.yaml", "r", encoding="utf-8") as f:
        mcp_server_config = yaml.safe_load(f)

    port = mcp_server_config['server_config'].get("mcp_server_port", 8704)

    # 启动信息
    logger.info("=" * 70)
    logger.info("启动 Gelab-MCP-Server (无状态 HTTP 模式)")
    logger.info(f"端口: {port}")
    logger.info(f"MCP 端点: http://127.0.0.1:{port}/mcp/")
    logger.info(f"健康检查: http://127.0.0.1:{port}/health")
    logger.info("=" * 70)

    print("")
    print("=" * 70)
    print("[启动] Gelab-MCP-Server 启动中...")
    print("[模式] 无状态 HTTP (最大兼容性)")
    print(f"[端点] MCP: http://127.0.0.1:{port}/mcp/")
    print(f"[健康检查] http://127.0.0.1:{port}/health")
    print("=" * 70)
    print("")

    # 启动服务器 - 使用无状态 HTTP 模式
    mcp.run(transport="http", host="127.0.0.1", port=port, stateless_http=True)
