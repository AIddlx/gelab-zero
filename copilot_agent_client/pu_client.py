import os
import sys
import logging

if "." not in sys.path:
    sys.path.append(".")

import json

from PIL import Image
import io

from tools.image_tools import draw_points, make_b64_url

from copilot_front_end.mobile_action_helper import capture_screenshot, dectect_screen_on, press_home_key

from copilot_front_end.mobile_action_helper import init_device, open_screen
from copilot_front_end.pu_frontend_executor import act_on_device, uiTars_to_frontend_action

from megfile import smart_remove

import time

from tools.ask_llm_v2 import ask_llm_anything

# 获取日志记录器
logger = logging.getLogger(__name__)


def _clean_base64_simple(messages):
    """简化版本：只显示摘要，不替换为文件路径"""
    if isinstance(messages, dict):
        cleaned = {}
        for k, v in messages.items():
            cleaned[k] = _clean_base64_simple(v)
        return cleaned
    elif isinstance(messages, list):
        cleaned = []
        for item in messages:
            cleaned.append(_clean_base64_simple(item))
        return cleaned
    elif isinstance(messages, str):
        if messages.startswith("data:image/"):
            try:
                if "," in messages:
                    prefix = messages.split(",")[0]
                    img_type = prefix.split("/")[1].split(";")[0]
                    b64_data = messages.split(",", 1)[1]
                    size_kb = len(b64_data) * 3 / 4 / 1024
                    return f"[BASE64_IMAGE: type={img_type}, size≈{size_kb:.1f}KB]"
            except:
                return f"[BASE64_IMAGE: length={len(messages)}]"
        return messages
    else:
        return messages


def reply_info_action(current_image_url, task, info_action, model_provider, model_name):
    """
    Reply with information action.
    """
    messages_to_ask = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text":  f"""# 角色
你将扮演一个正在使用GUI Agent完成任务的用户。

# 任务
阅读下方提供的所有背景信息，针对[Agent的澄清问题]，生成一个提供关键信息的、简短直接的回答。

# 背景信息
- **任务目标:** {task}
- **agent 问的问题:** {json.dumps(info_action, ensure_ascii=False)}

# 输出要求
- 你的回答必须极其简短和明确。
- 你的回答应直接命中问题的核心，解决Agent的疑惑。
- 不要进行任何额外的解释、对话或使用礼貌用语。
- 只输出回答本身，不要添加任何引号或其他修饰。

以下是当前页面内容:
                """,
                },
                {
                    'type': "image_url",
                    'image_url': {
                        'url': current_image_url
                    }
                },
                {
                    "type": "text",
                    "text": '请基于以上信息，简洁直接地回答Agent的问题。'
                }
            ]
        }
    ]

    response = ask_llm_anything(
        model_provider=model_provider,
        model_name=model_name,
        messages=messages_to_ask,
        args={
            "max_tokens": 1024,
            "temperature": 0.5,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
        }
    )

    if "</think>" in response:
        response = response.split("</think>")[-1].strip()

    return response

# delay after act on device
# rollout config
# device info
# def evaluate_task_on_device(agent_server, device_info, task, frontend_action_converter, ask_action_function_func, max_steps = 40, delay_after_capture = 2):
def evaluate_task_on_device(agent_server, device_info, task, rollout_config, extra_info = {}, reflush_app=True, auto_reply = False, reset_environment=True):
    """
    Evaluate a task on a device using the provided frontend action converter and action function.

    """
    logger.debug("evaluate_task_on_device 开始")
    logger.debug(f"任务: {task}, 设备: {device_info['device_id']}")

    # init device for the first time
    device_id = device_info['device_id']
    open_screen(device_id)
    init_device(device_id)

    if reset_environment:
        press_home_key(device_id, print_command=False)

    task, task_type = task, rollout_config['task_type']

    session_id = agent_server.get_session({
        "task": task,
        "task_type": task_type,
        "model_config": rollout_config['model_config'],
        "extra_info": extra_info
    })
    logger.debug(f"Session ID: {session_id}")

    return_log = {
        "session_id": session_id,
        "device_info": device_info,
        "task": task,
        "rollout_config": rollout_config,
        "extra_info": extra_info
    }

    device_id, device_wm_size = device_info['device_id'], device_info['device_wm_size']

    max_steps = rollout_config.get('max_steps', 40)
    delay_after_capture = rollout_config.get('delay_after_capture', 2)

    history_actions = []

    for step_idx in range(max_steps):
        logger.debug(f"Step {step_idx + 1}/{max_steps} 开始")

        if not dectect_screen_on(device_id):
            logger.warning("屏幕关闭，退出循环")
            break

        logger.debug("正在捕获设备截图...")
        image_path = capture_screenshot(device_id, "tmp_screenshot", print_command=False)
        logger.debug(f"截图已保存: {image_path}")

        image_b64_url = make_b64_url(image_path, resize_config=rollout_config['model_config'].get("resize_config", None))
        smart_remove(image_path)

        payload = {
            "session_id": session_id,
            "observation": {
                "screenshot": {
                    "type": "image_url",
                    "image_url": {
                        "url": image_b64_url
                    }
                },
            }
        }

        if history_actions[-1]['action_type'] == "INFO" if len(history_actions) > 0 else False:
            info_action = history_actions[-1]
            logger.debug(f"INFO 动作，需要回复: {info_action}")

            if auto_reply:
                reply_info = reply_info_action(image_b64_url, task, info_action, model_provider=rollout_config['model_config']['model_provider'], model_name=rollout_config['model_config']['model_name'])
                logger.debug(f"自动回复: {reply_info}")
            else:
                print(f"\n[Agent 询问] {info_action.get('value', '')}")
                reply_info = input("请回复: ")
                logger.debug(f"用户回复: {reply_info}")

            payload['observation']['query'] = reply_info

        action = agent_server.automate_step(payload)['action']
        action = uiTars_to_frontend_action(action)
        act_on_device(action, device_id, device_wm_size, print_command=False, reflush_app=reflush_app)
        history_actions.append(action)
        logger.debug(f"Step {step_idx+1} 完成. Action: {action.get('action_type', 'UNKNOWN')}")

        if action['action_type'].upper() in ['COMPLETE', "ABORT"]:
            logger.info(f"检测到终止动作: {action['action_type']}")
            break

        time.sleep(delay_after_capture)

    if action['action_type'] in ['COMPLETE', "ABORT"]:
        stop_reason = action['action_type']
    elif step_idx == max_steps - 1:
        stop_reason = "MAX_STEPS_REACHED"
    else:
        stop_reason = "MANUAL_STOP"

    return_log['stop_reason'] = stop_reason
    return_log['stop_steps'] = step_idx + 1

    logger.info(f"任务完成 - 步数: {len(history_actions)}, 原因: {stop_reason}")
    return return_log


