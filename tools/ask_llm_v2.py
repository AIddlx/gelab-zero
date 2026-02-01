import sys
import logging
if "." not in sys.path:
    sys.path.append(".")

from megfile import smart_open
import base64

from openai import OpenAI
import yaml

import json
import time

# 获取日志记录器
logger = logging.getLogger(__name__)

# 控制台输出模型回复的标志（默认开启）
_show_model_response = True

def set_show_model_response(show: bool):
    """设置是否在控制台显示模型回复"""
    global _show_model_response
    _show_model_response = show

def _print_model_response(response: str, max_len=200):
    """在控制台打印模型回复（简洁格式）"""
    if not _show_model_response:
        return

    # 清理回复内容，移除过长的思考过程
    lines = response.split('\n')
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过思考过程标记
        if line.startswith('<|thinking|>') or line.startswith('<|/thinking|>'):
            continue
        clean_lines.append(line)

    # 处理制表符分隔的字段（explain\taction\tvalue\tsummary）
    display_lines = []
    for line in clean_lines[:5]:  # 增加到5行以显示更多字段
        # 如果一行中包含多个制表符，说明是结构化输出，需要分行显示
        if '\t' in line and line.count('\t') >= 2:
            parts = line.split('\t')
            for part in parts:
                part = part.strip()
                if part:
                    # 提取字段名和值（如 "explain:xxx"）
                    if ':' in part:
                        field_name, field_value = part.split(':', 1)
                        # 限制每个字段的值长度
                        if len(field_value) > 100:
                            field_value = field_value[:100] + '...'
                        display_lines.append(f"   └─ {field_name}: {field_value}")
                    else:
                        display_lines.append(f"   └─ {part[:100]}{'...' if len(part) > 100 else ''}")
        else:
            # 限制单行长度
            if len(line) > 100:
                line = line[:100] + '...'
            display_lines.append(f"   └─ {line}")

    # 输出
    print('\n'.join(display_lines))

def ask_llm_anything(model_provider, model_name, messages, args= {
    "max_tokens": 256,
    "temperature": 0.5,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
}, resize_config=None):

    logger.debug(f"ask_llm_anything - 提供商: {model_provider}, 模型: {model_name}")

    with smart_open("model_config.yaml", "r", encoding="utf-8") as f:
        model_config = yaml.safe_load(f)

    if model_provider in model_config:
        client = OpenAI(
            api_key=model_config[model_provider]["api_key"],
            base_url=model_config[model_provider]["api_base"]
        )
    else:
        logger.error(f"未知的模型提供商: {model_provider}")
        raise ValueError(f"Unknown model provider: {model_provider}")

    # preprocess
    def preprocess_messages(messages):
        image_count = 0
        for msg in messages:
            if type(msg['content']) == str:
                continue
            assert type(msg['content']) == list
            for content in msg['content']:
                if content['type'] == "text":
                    continue
                assert content['type'] == "image_url" or content['type'] == "image_b64"
                if content['type'] == "image_url":
                    url = content['image_url']['url']
                    if url.startswith("data:image/"):
                        continue
                    else:
                        image_bytes = smart_open(url, mode="rb").read()
                        b64 = base64.b64encode(image_bytes).decode('utf-8')
                        if image_bytes[0:4] == b"\x89PNG":
                            content['image_url']['url'] = "data:image/png;base64," + b64
                        elif image_bytes[0:2] == b"\xff\xd8":
                            content['image_url']['url'] = "data:image/jpeg;base64," + b64
                        else:
                            content['image_url']['url'] = "data:image/png;base64," + b64
                        image_count += 1
                else:
                    assert content['type'] == "image_b64"
                    b64 = content['image_b64']['b64_json']
                    del content['image_b64']
                    content['image_url'] = {"url": "data:image/png;base64," + b64}
                    content['type'] = "image_url"

                if resize_config is not None and resize_config.get("is_resize", False) == True:
                    image_url = content['image_url']['url']
                    image_b64_url = image_url.split(",", 1)[1]
                    image_data = base64.b64decode(image_b64_url)
                    from PIL import Image
                    import io
                    image = Image.open(io.BytesIO(image_data))
                    image = image.resize(size= resize_config['target_image_size'])
                    image_data = io.BytesIO()
                    image = image.convert('RGB')
                    image.save(image_data, format="JPEG", quality=85)
                    image_data = image_data.getvalue()
                    b64_image = base64.b64encode(image_data).decode('utf-8')
                    content['image_url']['url'] = f"data:image/jpeg;base64,{b64_image}"

        logger.debug(f"预处理完成，处理了 {image_count} 张图片")
        return messages
    messages = preprocess_messages(messages)

    logger.debug("开始调用 OpenAI API...")
    start_time = time.time()
    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=args.get("temperature", 0.5),
        top_p=args.get("top_p", 1.0),
        frequency_penalty=args.get("frequency_penalty", 0.0),
        max_tokens=args.get("max_tokens", 100),
    )
    end_time = time.time()
    inference_time = end_time - start_time
    logger.debug(f"LLM 调用耗时: {inference_time:.2f}s，ID: {completion.id}")

    result = completion.choices[0].message.content

    reasoning = getattr(completion.choices[0].message, "reasoning_content", "")
    if reasoning is not None and len(reasoning) > 0:
        result = "</think>" + reasoning + "</think>" + "\n" + result

    # 在控制台显示模型回复（简洁格式）
    _print_model_response(result)

    return result
