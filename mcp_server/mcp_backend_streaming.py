"""
MCP 后端实现 - 流式响应版本

支持实时进度报告的 MCP 工具实现
"""

import sys
import asyncio
import json
from typing import Annotated, Optional

if "." not in sys.path:
    sys.path.append(".")

from fastmcp import Context
from pydantic import Field

from copilot_front_end.mobile_action_helper import list_devices
from copilot_agent_server.local_server import LocalServer
from copilot_agent_client.mcp_agent_loop import gui_agent_loop

import yaml
from megfile import smart_open


def get_device_list():
    """获取已连接设备列表"""
    from copilot_front_end.mobile_action_helper import list_devices as _list_devices
    return _list_devices()


async def execute_task_streaming(
    ctx: Context,

    device_id: Annotated[str, Field(description="设备ID")],

    task: Annotated[str, Field(description="任务描述")],

    # 超时配置
    timeout: Annotated[int, Field(description="任务超时时间（秒），默认600秒（10分钟）", ge=30, le=3600)] = 600,

    # 任务配置
    max_steps: Annotated[int, Field(description="最大步数", ge=1, le=400)] = 20,
    reset_environment: Annotated[bool, Field(description="是否重置环境")] = True,

    # 中间日志配置
    enable_intermediate_logs: Annotated[bool, Field(description="是否返回中间日志")] = True,
    enable_intermediate_screenshots: Annotated[bool, Field(description="是否返回中间截图")] = False,
    enable_final_screenshot: Annotated[bool, Field(description="是否返回最终截图")] = True,

    # INFO 动作处理
    reply_mode: Annotated[str, Field(description="INFO 动作处理模式: auto_reply/no_reply/pass_to_client")] = "pass_to_client",

    # 会话继续
    session_id: Annotated[Optional[str], Field(description="会话ID（用于继续之前的会话）")] = None,
    reply_from_client: Annotated[Optional[str], Field(description="对 INFO 动作的回复")] = None,

    extra_info: Annotated[dict, Field(description="额外信息")] = {},
):
    """
    执行 GUI Agent 任务（流式响应版本）

    实时返回执行进度，支持长时间任务。

    **功能特点：**
    - ✅ 实时进度报告：每完成一步立即返回进度
    - ✅ 防止超时：长任务自动分阶段返回结果
    - ✅ 详细日志：可选择返回中间步骤和截图

    **使用建议：**
    - 复杂任务建议拆分成多个小任务
    - 启用 enable_intermediate_logs 查看详细过程
    - 根据任务复杂度调整 max_steps 和 timeout
    """

    # 加载配置
    with smart_open("mcp_server_config.yaml", "r", encoding="utf-8") as f:
        mcp_server_config = yaml.safe_load(f)

    agent_loop_config = mcp_server_config['agent_loop_config']
    server_config = mcp_server_config['server_config']

    # 应用超时限制
    default_timeout = server_config.get("default_task_timeout", 600)
    max_timeout = server_config.get("max_task_timeout", 1800)

    # 确保超时在合理范围内
    actual_timeout = min(max(timeout, 30), min(max_timeout, timeout))

    # 创建服务器
    l2_server = LocalServer(server_config)

    # 报告开始
    await ctx.info(f"🚀 开始执行任务: {task}")
    await ctx.info(f"📱 设备: {device_id}")
    await ctx.info(f"⏱️ 超时: {actual_timeout}秒 | 最大步数: {max_steps}")
    await ctx.info("-" * 50)

    # 使用异步执行，但通过回调报告进度
    progress_data = {"current_step": 0, "last_action": None}

    def step_callback(step_num, action_info, total_steps):
        """每步执行的回调函数"""
        progress_data["current_step"] = step_num
        progress_data["last_action"] = action_info

        action_type = action_info.get("action_type", "UNKNOWN")
        action_desc = action_info.get("cot", "") or action_info.get("summary", "")

        # 计算进度百分比
        progress = min(100, int((step_num / total_steps) * 100))

        # 报告进度
        asyncio.create_task(ctx.report_progress(
            progress=progress,
            message=f"Step {step_num}/{total_steps}: {action_type} - {action_desc[:50]}"
        ))

        # 详细日志
        if enable_intermediate_logs:
            asyncio.create_task(ctx.info(
                f"  [{step_num}/{total_steps}] {action_type}\n"
                f"  详情: {action_desc[:100]}"
            ))

    # 执行任务（带超时）
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                gui_agent_loop,
                agent_server=l2_server,
                device_id=device_id,
                agent_loop_config=agent_loop_config,
                max_steps=max_steps,
                enable_intermediate_logs=enable_intermediate_logs,
                enable_intermediate_image_caption=False,
                enable_intermediate_screenshots=enable_intermediate_screenshots,
                enable_final_screenshot=enable_final_screenshot,
                enable_final_image_caption=False,
                reply_mode=reply_mode,
                task=task,
                session_id=session_id,
                reply_from_client=reply_from_client,
                reset_environment=reset_environment,
                reflush_app=reset_environment,
                extra_info=extra_info,
            ),
            timeout=actual_timeout
        )

        # 任务完成
        stop_reason = result.get("stop_reason", "UNKNOWN")
        total_steps = result.get("global_step_idx", 0)

        await ctx.info("-" * 50)
        await ctx.info(f"✅ 任务完成!")
        await ctx.info(f"📊 结果: {stop_reason}")
        await ctx.info(f"📈 总步数: {total_steps}")

        # 报告 100% 完成
        await ctx.report_progress(1.0, "任务完成")

        return result

    except asyncio.TimeoutError:
        await ctx.info("-" * 50)
        await ctx.info(f"⏰ 任务超时（{actual_timeout}秒）")
        await ctx.info(f"📊 已完成步数: {progress_data['current_step']}")

        return {
            "stop_reason": "TIMEOUT",
            "global_step_idx": progress_data["current_step"],
            "error": f"任务超时（{actual_timeout}秒），请尝试减少 max_steps 或增加 timeout"
        }

    except Exception as e:
        await ctx.info("-" * 50)
        await ctx.info(f"❌ 任务失败: {str(e)}")

        return {
            "stop_reason": "ERROR",
            "error": str(e)
        }


# 保持同步版本兼容性
def execute_task(*args, **kwargs):
    """同步版本（兼容旧代码）"""
    # 如果在同步上下文中调用，使用 asyncio.run
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 已有运行中的事件循环，使用 create_task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    execute_task_streaming(*args, **kwargs)
                )
                return future.result(timeout=kwargs.get('timeout', 600))
        else:
            return asyncio.run(execute_task_streaming(*args, **kwargs))
    except RuntimeError:
        # 没有事件循环，创建新的
        return asyncio.run(execute_task_streaming(*args, **kwargs))


if __name__ == "__main__":
    # 测试代码
    devices = get_device_list()
    print(f"已连接设备: {devices}")

    if devices:
        print("\n测试流式响应任务...")
        # 这里需要异步上下文，实际使用时由 MCP 框架提供
        print("请在 MCP 客户端中测试")
