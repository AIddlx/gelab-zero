"""
GELab Single-Action MCP Server

仿照 MAI-UI 设计，提供单一职责的 MCP 服务器：
- 无状态：每次调用独立
- 接收自然语言指令
- 预测动作 → 执行动作 → 返回结果
- 返回文件路径（而非 base64 数据）

设计理念：
- 上层 AI（Claude）：理解任务、分解步骤、维护上下文、发送自然语言指令
- MCP 服务器：接收指令 + 截图 → LLM 预测动作 → 执行动作 → 返回结果 + 新截图路径

可用工具：
1. screenshot - 获取设备截图，返回文件路径
2. do_action - 执行单步动作，返回思考、动作、结果、执行后截图路径
"""

import sys
import os
import base64
import logging
import json
import re
import time
from io import BytesIO
from typing import Annotated, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP, Context
from fastmcp.utilities.logging import configure_logging
from pydantic import Field
from PIL import Image
from openai import OpenAI

# 添加项目路径
if "." not in sys.path:
    sys.path.append(".")

from copilot_front_end.scrcpy_connection_manager import get_scrcpy_manager

# 配置日志
log_dir = Path("running_log/mcp_server")
log_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now()
log_file = log_dir / f"single_action_mcp_{timestamp.strftime('%Y%m%d_%H%M%S')}.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

configure_logging(level='WARNING')
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastmcp").setLevel(logging.WARNING)

logger.info("=" * 70)
logger.info("Single-Action MCP 服务器初始化")
logger.info(f"日志文件: {log_file}")
logger.info("=" * 70)

# 截图保存目录
screenshot_dir = Path("running_log/mcp_screenshots")
screenshot_dir.mkdir(parents=True, exist_ok=True)

# 读取模型配置
import yaml
with open("model_config.yaml", "r", encoding="utf-8") as f:
    model_config = yaml.safe_load(f)

local_config = model_config.get("local", {})
llm_base_url = local_config.get("api_base", "http://localhost:11434/v1")
llm_api_key = local_config.get("api_key", "ollama")
model_name = "gelab-zero-4b-preview"

# 创建 OpenAI 客户端
llm_client = OpenAI(
    base_url=llm_base_url,
    api_key=llm_api_key
)

# 创建 FastMCP 服务器
mcp = FastMCP(
    name="Gelab-Single-Action-MCP",
    instructions="""
This MCP server provides single-action execution for Android device automation.

Design Philosophy:
- Stateless: Each call is independent
- Takes natural language instruction
- Predicts action using vision model → Executes action → Returns result + new screenshot

Upper AI (Claude) responsibilities:
- Understand the complete task
- Break down into steps
- Maintain context and progress
- Send natural language instructions

MCP Server responsibilities:
- Take instruction and screenshot
- Use vision model to predict action
- Execute the action
- Return thinking, action, result, and new screenshot path
"""
)


def _save_screenshot(pil_image: Image.Image, prefix: str = "screenshot") -> str:
    """
    保存截图到文件并返回路径

    Args:
        pil_image: PIL Image 对象
        prefix: 文件名前缀

    Returns:
        str: 截图文件的绝对路径
    """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 毫秒精度
    filename = f"{prefix}_{timestamp_str}.png"
    filepath = screenshot_dir / filename
    pil_image.save(filepath)
    return str(filepath.absolute())


def _parse_action_response(text: str) -> Dict[str, Any]:
    """
    解析模型输出，提取动作

    格式：<invoke>{"action": "click", "coordinate": [x, y]}</invoke>
    """
    result = {
        "thinking": None,
        "action": None,
    }

    # 提取 thinking
    thinking_pattern = r"<thinking>(.*?)</thinking>"
    thinking_match = re.search(thinking_pattern, text, re.DOTALL)
    if thinking_match:
        result["thinking"] = thinking_match.group(1).strip()

    # 提取 action JSON
    invoke_pattern = r"<invoke>\s*(\{.*?\})\s*</invoke>"
    invoke_match = re.search(invoke_pattern, text, re.DOTALL)
    if invoke_match:
        action_json = invoke_match.group(1).strip()
        try:
            result["action"] = json.loads(action_json)
        except json.JSONDecodeError:
            result["action"] = None

    return result


def _execute_action(device_id: str, action: Dict[str, Any]) -> str:
    """
    执行动作

    Args:
        device_id: 设备 ID
        action: 动作字典

    Returns:
        str: 执行结果描述
    """
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=False)

    if not client or not client.is_connected:
        return f"错误：设备 {device_id} 未连接"

    action_type = action.get("action")

    try:
        if action_type in ["click", "tap"]:
            coord = action.get("coordinate", [])
            if len(coord) >= 2:
                x, y = int(coord[0]), int(coord[1])
                client.tap(x, y)
                return f"已点击 ({x}, {y})"
            else:
                return f"错误：坐标格式不正确 {coord}"

        elif action_type == "swipe":
            start = action.get("start", [])
            end = action.get("end", [])
            duration_ms = action.get("duration_ms", 300)
            if len(start) >= 2 and len(end) >= 2:
                x1, y1 = int(start[0]), int(start[1])
                x2, y2 = int(end[0]), int(end[1])
                client.swipe(x1, y1, x2, y2, duration_ms)
                return f"已从 ({x1}, {y1}) 滑动到 ({x2}, {y2})"
            else:
                return f"错误：坐标格式不正确"

        elif action_type == "input_text":
            text = action.get("text", "")
            client.input_text(text)
            return f"已输入文本：{text[:50]}..." if len(text) > 50 else f"已输入文本：{text}"

        elif action_type == "press_key":
            key = action.get("key", "")
            client.press_key(key)
            return f"已按键：{key}"

        elif action_type == "home":
            client.home()
            return "已按 Home 键"

        elif action_type == "back":
            client.back()
            return "已按 Back 键"

        elif action_type == "wait":
            duration = action.get("duration", 1)
            time.sleep(duration)
            return f"已等待 {duration} 秒"

        elif action_type in ["terminate", "answer"]:
            # 这些是任务完成动作，不需要实际执行
            status = action.get("status", "completed")
            text = action.get("text", "")
            return f"任务动作：{action_type} - {text}"

        else:
            return f"不支持的动作类型：{action_type}"

    except Exception as e:
        return f"执行动作失败：{e}"


# System prompt for action prediction
ACTION_PREDICTION_SYSTEM_PROMPT = """你是一个 Android 手机自动化助手的动作预测模块。

你的任务：根据用户的指令和当前屏幕截图，返回一个动作来执行。

## 输出格式
<thinking>
简要说明：1) 你看到了什么 2) 你要执行什么操作 3) 为什么这样做能完成任务
</thinking>
<invoke>
{"action": "click|tap|swipe|input_text|press_key|home|back|wait|terminate|answer", ...}
</invoke>

## 可用动作
- click/tap: {"action": "click", "coordinate": [x, y], "button": "left|right"} - 点击坐标(像素)
- swipe: {"action": "swipe", "start": [x1, y1], "end": [x2, y2], "duration_ms": 300} - 滑动
- input_text: {"action": "input_text", "text": "内容"} - 输入文本
- press_key: {"action": "press_key", "key": "HOME|BACK|ENTER|MENU|VOLUME_UP|VOLUME_DOWN"} - 按键
- home: {"action": "home"} - 按 Home 键
- back: {"action": "back"} - 返回键
- wait: {"action": "wait", "duration": 1} - 等待（秒）
- terminate: {"action": "terminate", "status": "success"} - 任务完成
- answer: {"action": "answer", "text": "结果"} - 返回答案

## 重要规则
1. 坐标使用像素值，根据截图尺寸推断
2. 只返回一个动作，不要返回多个动作
3. 仔细看截图，理解当前屏幕状态
4. 如果需要输入文本后确认，可以分两步：先 input_text，再按返回时告诉用户需要 press_key("ENTER")
5. 坐标系：左上角是(0,0)，右下角是(宽度,高度)
"""


@mcp.tool
def list_devices() -> list:
    """
    列出所有已连接的设备

    Returns:
        list: 设备 ID 列表
    """
    manager = get_scrcpy_manager()
    devices = manager.list_connected_devices()
    logger.info(f"已连接设备: {devices}")
    return devices


@mcp.tool
async def screenshot(
    device_id: Annotated[str, Field(description="设备 ID")],
) -> dict:
    """
    获取设备截图并保存到文件

    Args:
        device_id: 设备 ID

    Returns:
        dict: 包含截图文件路径、宽度、高度
    """
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=False)

    if not client or not client.is_connected:
        return {"error": f"设备 {device_id} 未连接"}

    # 获取最后一帧
    frame = client.last_frame
    if frame is None:
        client.start()
        time.sleep(0.5)
        frame = client.last_frame

    if frame is None:
        return {"error": "无法获取截图"}

    # 转换为 PIL Image
    from scrcpy_py_ddlx_client.utils import convert_frame_to_image
    pil_image = convert_frame_to_image(frame)

    width, height = pil_image.size

    # 保存截图
    filepath = _save_screenshot(pil_image, "screenshot")

    logger.info(f"截图已保存: {filepath}, 尺寸: {width}x{height}")

    return {
        "device_id": device_id,
        "path": filepath,
        "width": width,
        "height": height,
        "success": True
    }


@mcp.tool
async def do_action(
    device_id: Annotated[str, Field(description="设备 ID")],
    instruction: Annotated[str, Field(description="自然语言指令（如'点击搜索框'、'输入Hello'）")],
    screenshot_path: Annotated[Optional[str], Field(description="当前截图文件路径（可选，为空则自动获取）")] = None,
) -> dict:
    """
    执行单步动作

    这是 MCP 的核心功能：
    1. 获取当前截图（如果未提供）
    2. 调用视觉模型预测动作
    3. 执行动作
    4. 获取执行后的截图
    5. 返回完整结果

    Args:
        device_id: 设备 ID
        instruction: 自然语言指令
        screenshot_path: 当前截图路径（可选）

    Returns:
        dict: 包含 thinking（思考）、predicted_action（预测的动作）、executed（是否执行成功）、
              execution_result（执行结果）、screenshot_after_path（执行后截图路径）
    """
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=False)

    if not client or not client.is_connected:
        return {
            "error": f"设备 {device_id} 未连接",
            "thinking": None,
            "predicted_action": None,
            "executed": False,
            "execution_result": None,
            "screenshot_after_path": None
        }

    # 1. 获取当前截图
    if screenshot_path:
        # 使用提供的截图
        pil_image = Image.open(screenshot_path)
    else:
        # 自动获取截图
        frame = client.last_frame
        if frame is None:
            client.start()
            time.sleep(0.5)
            frame = client.last_frame

        if frame is None:
            return {
                "error": "无法获取截图",
                "thinking": None,
                "predicted_action": None,
                "executed": False,
                "execution_result": None,
                "screenshot_after_path": None
            }

        from scrcpy_py_ddlx_client.utils import convert_frame_to_image
        pil_image = convert_frame_to_image(frame)

    width, height = pil_image.size

    # 2. 调用 LLM 预测动作
    screenshot_base64 = _encode_image_to_base64(pil_image)

    screen_info = f"\n当前屏幕尺寸: {width}x{height} 像素"
    user_message = f"{instruction}{screen_info}"

    messages = [
        {
            "role": "system",
            "content": ACTION_PREDICTION_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_message},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_base64}"
                    }
                }
            ]
        }
    ]

    try:
        response = llm_client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=2048,
            temperature=0.1
        )

        raw_output = response.choices[0].message.content.strip()
        result = _parse_action_response(raw_output)
        result["raw_output"] = raw_output

        thinking = result.get("thinking", "")
        predicted_action = result.get("action")

        logger.info(f"do_action: instruction='{instruction}', action={predicted_action}")
        logger.debug(f"原始输出: {raw_output}")

        # 3. 执行动作
        executed = False
        execution_result = None

        if predicted_action:
            execution_result = _execute_action(device_id, predicted_action)
            executed = "错误" not in execution_result

            # 等待动作生效
            time.sleep(0.5)

        # 4. 获取执行后的截图
        frame_after = client.last_frame
        if frame_after is None:
            # 尝试重新获取
            time.sleep(0.3)
            frame_after = client.last_frame

        screenshot_after_path = None
        if frame_after is not None:
            from scrcpy_py_ddlx_client.utils import convert_frame_to_image
            pil_image_after = convert_frame_to_image(frame_after)
            screenshot_after_path = _save_screenshot(pil_image_after, "after")

        return {
            "thinking": thinking,
            "predicted_action": predicted_action,
            "executed": executed,
            "execution_result": execution_result,
            "screenshot_after_path": screenshot_after_path,
            "success": True
        }

    except Exception as e:
        logger.error(f"do_action 错误: {e}")
        return {
            "thinking": None,
            "predicted_action": None,
            "executed": False,
            "execution_result": f"执行失败: {e}",
            "screenshot_after_path": None,
            "error": str(e)
        }


def _encode_image_to_base64(pil_image: Image.Image) -> str:
    """将 PIL Image 编码为 base64 字符串"""
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


if __name__ == "__main__":
    import yaml

    # 加载配置
    with open("mcp_server_config.yaml", "r", encoding="utf-8") as f:
        mcp_server_config = yaml.safe_load(f)

    port = mcp_server_config['server_config'].get("single_action_mcp_port", 8705)

    logger.info("=" * 70)
    logger.info("启动 Gelab-Single-Action-MCP")
    logger.info(f"端口: {port}")
    logger.info(f"MCP 端点: http://127.0.0.1:{port}/mcp/")
    logger.info(f"LLM: {llm_base_url}, 模型: {model_name}")
    logger.info(f"截图目录: {screenshot_dir.absolute()}")
    logger.info("=" * 70)

    print("")
    print("=" * 70)
    print("[启动] Gelab-Single-Action-MCP 启动中...")
    print("[模式] 单步动作执行（接收自然语言指令）")
    print(f"[端点] http://127.0.0.1:{port}/mcp/")
    print(f"[LLM] {llm_base_url}")
    print(f"[模型] {model_name}")
    print(f"[截图] {screenshot_dir.absolute()}")
    print("=" * 70)
    print("")

    # 启动服务器
    mcp.run(transport="http", host="127.0.0.1", port=port, stateless_http=True)
