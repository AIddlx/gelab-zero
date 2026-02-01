import json
import sys
import os
import logging

from copilot_agent_server.base_server import BaseCopilotServer

from copilot_agent_server.local_server_logger import LocalServerLogger

from tools.image_tools import read_from_url, make_b64_url

from copilot_agent_server.parser_factory import get_parser

from tools.ask_llm_v2 import ask_llm_anything

from copy import deepcopy

import time

# 获取日志记录器
logger = logging.getLogger(__name__)


def clean_base64_in_messages(messages, environments=None):
    """
    清理消息中的 base64 图片数据，替换为文件路径引用

    Args:
        messages: 要清理的消息（asked_messages）
        environments: 环境列表，包含实际的图片文件路径
    """
    if environments is None:
        # 如果没有提供 environments，使用简化版本（只显示摘要）
        return _clean_base64_simple(messages)

    # 创建图片路径映射
    image_paths = set()
    for env in environments:
        if isinstance(env, dict) and 'image' in env:
            img_path = env['image']
            if isinstance(img_path, str) and not img_path.startswith('data:'):
                image_paths.add(img_path)

    if isinstance(messages, dict):
        cleaned = {}
        for k, v in messages.items():
            cleaned[k] = clean_base64_in_messages(v, environments)
        return cleaned
    elif isinstance(messages, list):
        cleaned = []
        for item in messages:
            cleaned.append(clean_base64_in_messages(item, environments))
        return cleaned
    elif isinstance(messages, str):
        # 检查是否是 base64 图片 URL
        if messages.startswith("data:image/"):
            # 尝试匹配已保存的图片文件
            # 从 image_paths 中选择一个合适的路径
            if image_paths:
                # 使用最新的图片路径（通常是对应当前步骤的图片）
                img_path = list(image_paths)[-1]
                return f"[IMAGE_FILE: {img_path}]"
            else:
                # 回退到显示摘要信息
                try:
                    if "," in messages:
                        prefix = messages.split(",")[0]
                        img_type = prefix.split("/")[1].split(";")[0]
                        size_kb = len(messages.split(",", 1)[1]) * 3 / 4 / 1024
                        return f"[BASE64_IMAGE: type={img_type}, size≈{size_kb:.1f}KB]"
                except:
                    return f"[BASE64_IMAGE: length={len(messages)}]"
        return messages
    else:
        return messages


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


class LocalServer(BaseCopilotServer):
    
    def __init__(self, server_config: dict):
        super().__init__()


        self.server_config = server_config

        # assert log related config
        assert "log_dir" in server_config, "server_config must contain 'log_dir'"
        assert "image_dir" in server_config, "server_config must contain 'image_dir'"

        self.debug = server_config.get("debug", False)
        

    
    def get_session(self, payload: dict) -> str:
        """
        Get a new session ID.
        """
        logger.debug(f"LocalServer.get_session 开始，payload: {_clean_base64_simple(payload)}")

        import uuid
        session_id = str(uuid.uuid4())

        server_logger = LocalServerLogger({
            "log_dir": self.server_config["log_dir"],
            "image_dir": self.server_config["image_dir"],
            "session_id": session_id
        })

        assert "task" in payload, "payload must contain 'task'"
        assert "task_type" in payload, "payload must contain 'task_type' indicating different parsers"
        assert "model_config" in payload, "payload must contain 'model_config'"

        model_config = payload["model_config"]
        assert "model_name" in model_config, "model_config must contain 'model_name'"

        extra_info = payload.get('extra_info', {})

        message_to_log = {
            "log_type": "session_start",
            "task": payload["task"],
            "task_type": payload["task_type"],
            "model_config": payload["model_config"],
            "extra_info": extra_info
        }

        server_logger.log_str(message_to_log, is_print=self.debug)
        return session_id

    def automate_step(self, payload: dict) -> dict:
        """
        Automate a step in the Copilot service.
        """
        assert "session_id" in payload, "payload must contain 'session_id'"
        session_id = payload["session_id"]

        server_logger = LocalServerLogger({
            "log_dir": self.server_config["log_dir"],
            "image_dir": self.server_config["image_dir"],
            "session_id": session_id
        })

        logs = server_logger.read_logs()
        assert len(logs) > 0, f"No logs found for session_id {session_id}"
        current_ste = len(logs) - 1

        config_log = logs[0]
        config_dict = config_log['message']
        task_type = config_dict['task_type']
        model_config = config_dict['model_config']
        task = config_dict['task']

        logger.debug(f"步骤 {current_ste} - 任务类型: {task_type}")

        # current image
        assert "observation" in payload, "payload must contain 'observation'"
        observation = payload['observation']
        image_url = observation['screenshot']['image_url']['url']

        image = read_from_url(image_url)
        image_inner_url = server_logger.save_image(image, f"step_{current_ste+1}")

        query = observation.get('query', '')

        def get_envs_acts_from_logs(logs):
            environments = []
            actions = []
            for log in logs[1:]:
                msg = log['message']
                assert "environment" in msg, "log message must contain 'environment'"
                assert "action" in msg, "log message must contain 'action'"
                environments.append(msg['environment'])
                actions.append(msg['action'])
            return environments, actions

        environments, actions = get_envs_acts_from_logs(logs)

        current_env = {
            "image": image_inner_url,
            "user_comment": query
        }
        environments.append(current_env)

        parser = get_parser(task_type)
        messages_to_ask = parser.env2messages4ask(
            task = task,
            environments = environments,
            actions = actions,
        )
        asked_messages = deepcopy(messages_to_ask)

        model_name = model_config['model_name']
        model_provider = model_config.get('model_provider', 'eval')
        args = model_config.get('args', {
            "temperature": 0.1,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "max_tokens": 512,
        })

        image_preprocess = model_config.get('image_preprocess', None)

        if image_preprocess is not None:
            if "target_image_size" in image_preprocess:
                target_image_size = image_preprocess["target_image_size"]
                logger.debug(f"调整图片尺寸到: {target_image_size}")

                def resize_image_in_messages(messages, target_size):
                    for msg in messages:
                        if type(msg['content']) == str:
                            continue
                        assert type(msg['content']) == list
                        for content in msg['content']:
                            if content['type'] == "text":
                                continue
                            assert content['type'] == "image_url"
                            image_url = content['image_url']['url']
                            image_resize_url = make_b64_url(image_url, resize_config={
                                "is_resize": True,
                                "target_image_size": target_size
                            })
                            content['image_url']['url'] = image_resize_url

                resize_image_in_messages(messages_to_ask, target_image_size)

        llm_start_time = time.time()
        response = ask_llm_anything(
            model_provider=model_provider,
            model_name=model_name,
            messages=messages_to_ask,
            args=args
        )
        llm_end_time = time.time()

        action = parser.str2action(response)

        # 构造日志消息
        log_message = {
            "environment": current_env,
            "action": action,
            "asked_messages": clean_base64_in_messages(asked_messages, environments),
            "model_response": response,
            "model_config": model_config,
            "llm_cost": {
                "llm_time": llm_end_time - llm_start_time,
                "llm_start_time": llm_start_time,
                "llm_end_time": llm_end_time
            },
        }

        server_logger.log_str(log_message, is_print=self.debug)

        return {
            "action": action,
            "current_step": current_ste + 1
        }