
import os
import sys
import time
import logging
import threading
from datetime import datetime
if "." not in sys.path:
    sys.path.append(".")

from copilot_agent_client.pu_client import evaluate_task_on_device
from copilot_front_end.mobile_action_helper import list_devices, get_device_wm_size
from copilot_agent_server.local_server import LocalServer, _clean_base64_simple

# ===== 日志配置 =====
def setup_logging(log_dir="running_log/logs"):
    """配置日志系统
    - 控制台: 只显示 INFO 及以上（简要信息）
    - run_single_task_xxx.log: 记录所有级别（详细信息，含 DEBUG）
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 结构化日志文件 - 记录所有级别
    log_file = os.path.join(log_dir, f"run_single_task_{timestamp}.log")

    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 捕获所有级别

    # 清除现有处理器
    logger.handlers.clear()

    # 文件处理器 - 记录所有级别（DEBUG 及以上）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 控制台处理器 - 只显示关键信息（WARNING 及以上）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    class ConsoleFormatter(logging.Formatter):
        def __init__(self):
            super().__init__()
            self.simple_fmt = logging.Formatter('%(message)s')
            self.level_fmt = logging.Formatter('%(levelname)s: %(message)s')
        def format(self, record):
            if record.levelno >= logging.ERROR:
                return self.level_fmt.format(record)
            return self.simple_fmt.format(record)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)

    # 过滤第三方库的 DEBUG 日志
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    # 过滤 OpenAI 库的 DEBUG 日志（避免打印完整的 base64 数据）
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('openai._base_client').setLevel(logging.WARNING)
    # 过滤 scrcpy 库的所有 INFO 及以下级别日志
    logging.getLogger('scrcpy_py_ddlx').setLevel(logging.ERROR)
    logging.getLogger('scrcpy_py_ddlx.core.demuxer.video').setLevel(logging.ERROR)
    logging.getLogger('scrcpy_py_ddlx.core.decoder.video').setLevel(logging.ERROR)

    logging.info(f"日志文件创建于: {log_file}")

    return log_file

# ===== 控制台简洁输出 =====
def console_print(msg, level="INFO"):
    """向控制台输出关键信息（独立于日志系统）"""
    if level == "ERROR":
        print(f"❌ {msg}")
    elif level == "WARN":
        print(f"⚠️  {msg}")
    elif level == "SUCCESS":
        print(f"✅ {msg}")
    elif level == "STEP":
        print(f"▶ {msg}")
    else:
        print(msg)

tmp_server_config = {
    "log_dir": "running_log/server_log/os-copilot-local-eval-logs/traces",
    "image_dir": "running_log/server_log/os-copilot-local-eval-logs/images",
    "debug": False
}


local_model_config = {
    "task_type": "parser_0922_summary",
    "model_config": {
        "model_name": "gelab-zero-4b-preview",
        "model_provider": "local",
        "args": {
            "temperature": 0.1,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "max_tokens": 4096,
        },
        
        # optional to resize image
        # "resize_config": {
        #     "is_resize": True,
        #     "target_image_size": (756, 756)
        # }
    },

    "max_steps": 400,
    "delay_after_capture": 2,
    "debug": False
}


# ===== 新增：用于记录每步耗时 =====
_step_times = []


# ===== 新增：包装 automate_step 方法 =====
def _format_action_for_display(action):
    """格式化动作信息用于显示"""
    if not isinstance(action, dict):
        return str(action)

    action_type = action.get('action_type', action.get('action', 'UNKNOWN'))
    info_parts = [action_type]

    if action_type == 'CLICK':
        point = action.get('point', action.get('coordinate', {}))
        if isinstance(point, dict):
            x = point.get('x', 0)
            y = point.get('y', 0)
            info_parts.append(f"({x:.2f}, {y:.2f})")
        label = action.get('label', '')
        if label:
            info_parts.append(f'"{label[:20]}"' if len(label) > 20 else f'"{label}"')

    elif action_type == 'TYPE':
        text = action.get('text', action.get('value', ''))
        if text:
            text_display = text[:30] + "..." if len(text) > 30 else text
            info_parts.append(f'"{text_display}"')

    elif action_type == 'SWIPE':
        start = action.get('start', action.get('point_start', {}))
        end = action.get('end', action.get('point_end', {}))
        direction = action.get('direction', '')
        if direction:
            info_parts.append(direction)
        elif start and end:
            info_parts.append(f"({start.get('x',0):.1f},{start.get('y',0):.1f})→({end.get('x',0):.1f},{end.get('y',0):.1f})")

    elif action_type == 'INFO':
        value = action.get('value', action.get('question', ''))
        if value:
            value_display = value[:40] + "..." if len(value) > 40 else value
            info_parts.append(f'"{value_display}"')

    elif action_type == 'WAIT':
        seconds = action.get('seconds', action.get('value', 0))
        info_parts.append(f"{seconds}s")

    elif action_type == 'COMPLETE':
        reason = action.get('reason', '')
        if reason:
            info_parts.append(f'"{reason[:30]}"' if len(reason) > 30 else f'"{reason}"')

    return " ".join(info_parts)


def _print_action_details(action):
    """打印动作详细信息（多行显示）"""
    if not isinstance(action, dict):
        return

    explain = action.get('explain', '')
    summary = action.get('summary', '')
    return_info = action.get('return', '')

    if explain:
        print(f"    说明: {explain[:100]}{'...' if len(explain) > 100 else ''}")
    if summary:
        print(f"    摘要: {summary[:100]}{'...' if len(summary) > 100 else ''}")
    if return_info:
        print(f"    返回: {return_info[:100]}{'...' if len(return_info) > 100 else ''}")


def _format_result_for_log(result):
    """格式化 result 用于日志输出"""
    if not isinstance(result, dict):
        return str(result)

    lines = []
    action = result.get('action', {})

    if not isinstance(action, dict):
        return str(result)

    # 定义需要处理的字段及其顺序
    field_order = ['action_type', 'action', 'THINK', 'think', 'explain', 'return', 'summary',
                   'value', 'text', 'point', 'label', 'coordinate', 'direction',
                   'point1', 'point2', 'seconds', 'reason']

    # 定义需要截断的字段及其最大长度
    max_lengths = {
        'THINK': 300,
        'think': 300,
        'explain': 200,
        'return': 200,
        'summary': 200,
        'value': 100,
        'text': 100,
        'label': 50,
    }

    # 按顺序处理字段
    for field in field_order:
        if field not in action:
            continue

        value = action[field]

        # 跳过空值
        if not value and value != 0 and value is not False:
            continue

        # 特殊处理 THINK 字段
        if field in ('THINK', 'think'):
            # 清理 THINK 中的换行和多余空格
            value_clean = ' '.join(str(value).split())
            max_len = max_lengths.get(field, 300)
            if len(value_clean) > max_len:
                value_clean = value_clean[:max_len] + '...'
            lines.append(f"{field}: {value_clean}")
        # 特殊处理字典类型字段（如 point）
        elif isinstance(value, dict):
            lines.append(f"{field}: {value}")
        # 其他字符串字段
        else:
            value_str = str(value)
            max_len = max_lengths.get(field, 200)
            if len(value_str) > max_len:
                value_str = value_str[:max_len] + '...'
            lines.append(f"{field}: {value_str}")

    return "\n  ".join(lines)


def wrap_automate_step_with_timing(server_instance, logger=None, max_steps=400):
    """包装 automate_step 方法，添加计时和日志记录"""
    if logger is None:
        logger = logging.getLogger(__name__)

    original_method = server_instance.automate_step

    def timed_automate_step(payload):
        step_num = len(_step_times) + 1
        logger.debug(f"===== Step {step_num} 开始 =====")
        logger.debug(f"Payload: {_clean_base64_simple(payload)}")

        step_start = time.time()
        result = None
        try:
            result = original_method(payload)
            logger.debug(f"Result:\n  {_format_result_for_log(result)}")

            # 显示截图文件路径
            session_id = payload.get("session_id", "unknown")
            image_dir = tmp_server_config.get("image_dir", "running_log/server_log/os-copilot-local-eval-logs/images")
            screenshot_path = f"{image_dir}/{session_id}_step_{step_num}.jpeg"
            console_print(f"  📸 截图: {screenshot_path}")

        except Exception as e:
            logger.error(f"Step {step_num} 执行出错: {e}", exc_info=True)
            console_print(f"Step {step_num} 执行出错: {e}", "ERROR")
            raise
        finally:
            duration = time.time() - step_start
            _step_times.append(duration)

            # 提取并显示动作信息
            action_display = ""
            action = None
            if isinstance(result, dict) and 'action' in result:
                action = result['action']
                action_display = _format_action_for_display(action)

            console_print(f"Step {step_num}/{max_steps} ({duration:.1f}s) - {action_display}", "STEP")
            _print_action_details(action)
            logger.debug(f"Step {step_num} 耗时: {duration:.2f} 秒")

        return result

    # 替换实例方法
    server_instance.automate_step = timed_automate_step

if __name__ == "__main__":
    # 初始化日志
    log_file = setup_logging()
    logger = logging.getLogger(__name__)

    # 详细日志记录到文件
    logger.info("=" * 60)
    logger.info("程序启动")
    logger.info("=" * 60)
    logger.info(f"命令行参数: {sys.argv}")

    if len(sys.argv) < 2:
        console_print("错误：未传入任务参数！", "ERROR")
        print("使用方法：")
        print(f"  python {sys.argv[0]} \"你的任务描述\"")
        print("  示例: python script.py \"去淘宝帮我买本书\"")
        logger.error("未传入任务参数，程序退出")
        sys.exit(1)

    task = ' '.join(sys.argv[1:])
    logger.info(f"任务描述: {task}")

    # 获取设备信息
    device_list = list_devices()

    # 如果没有检测到设备，尝试自动发现和连接
    if not device_list:
        console_print("未检测到已连接设备，尝试自动发现...", "WARN")
        import subprocess
        import re
        try:
            connected = False

            # 策略1: 检查是否有 USB 设备，自动启用无线
            result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=5)
            usb_device = None

            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('List of devices'):
                    continue
                parts = line.split()
                # USB 设备：至少 2 列，第一列不含冒号
                if len(parts) >= 2 and 'device' in line and ':' not in parts[0]:
                    usb_device = parts[0]
                    break

            if usb_device:
                console_print(f"✅ 检测到 USB 设备: {usb_device}", "INFO")
                console_print("正在自动启用无线模式...", "INFO")

                # 步骤1: 启用 TCP/IP
                tcpip_result = subprocess.run(
                    ["adb", "-s", usb_device, "tcpip", "5555"],
                    capture_output=True, text=True, timeout=15
                )

                if tcpip_result.returncode != 0:
                    console_print(f"启用 TCP/IP 失败: {tcpip_result.stderr}", "ERROR")
                    sys.exit(1)

                console_print("✅ TCP/IP 模式已启用", "INFO")

                # 步骤2: 从设备获取 IP 地址（使用验证过的方法）
                interfaces = ["wlan0", "wifi0", "wlan1", "eth0"]
                device_ip = None

                for interface in interfaces:
                    console_print(f"正在从 {interface} 获取 IP 地址...", "INFO")
                    ip_result = subprocess.run(
                        ["adb", "-s", usb_device, "shell", "ip", "addr", "show", interface],
                        capture_output=True, text=True, timeout=5
                    )

                    # 提取 IP 地址
                    for match in re.finditer(r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', ip_result.stdout):
                        ip = match.group(1)
                        # 过滤掉特殊地址
                        if not ip.startswith(('127.', '169.254.', '0.0.0.')):
                            device_ip = ip
                            console_print(f"✅ 找到设备 IP: {device_ip} ({interface})", "INFO")
                            break
                    if device_ip:
                        break

                if not device_ip:
                    console_print("无法获取设备 IP 地址", "ERROR")
                    console_print("请确保手机连接了 WiFi", "ERROR")
                    sys.exit(1)

                # 步骤3: 建立无线连接
                wireless_addr = f"{device_ip}:5555"
                console_print(f"正在连接到 {wireless_addr}...", "INFO")
                connect_result = subprocess.run(
                    ["adb", "connect", wireless_addr],
                    capture_output=True, text=True, timeout=10
                )

                if "connected" in connect_result.stdout.lower() or "already connected" in connect_result.stdout.lower():
                    console_print(f"✅ 无线连接成功: {wireless_addr}", "SUCCESS")
                    console_print("💡 USB 线已可安全拔除，设备保持无线连接", "INFO")
                    connected = True
                else:
                    console_print(f"无线连接失败: {connect_result.stderr}", "ERROR")
                    sys.exit(1)

            # 策略2: 如果没有 USB，扫描局域网寻找 ADB 设备
            if not connected:
                console_print("未检测到 USB 设备，正在扫描局域网...", "INFO")

                # 获取本机 IP 和网段
                import socket
                local_ip = None
                try:
                    # 创建一个 UDP socket 连接到外部地址来获取本机 IP
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.settimeout(2)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                except Exception:
                    local_ip = "192.168.1.1"  # 默认值

                console_print(f"本机 IP: {local_ip}", "INFO")

                # 提取网段（如 192.168.1.0/24）
                ip_parts = local_ip.split('.')
                network_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"

                console_print(f"正在扫描网段 {network_prefix}.0/24 中的无线设备...", "INFO")

                # 扫描网段内常见 IP 范围（1-254）
                # 使用多线程加速扫描
                from concurrent.futures import ThreadPoolExecutor, as_completed
                import socket

                def check_adb_port(ip):
                    """检查指定 IP 的 5555 端口是否开放"""
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.5)
                        result = sock.connect_ex((ip, 5555))
                        sock.close()
                        return ip if result == 0 else None
                    except Exception:
                        return None

                # 扫描常见 IP 范围
                found_devices = []
                console_print("正在扫描设备（这可能需要 10-30 秒）...", "INFO")

                with ThreadPoolExecutor(max_workers=50) as executor:
                    futures = {}
                    for i in range(1, 255):
                        ip = f"{network_prefix}.{i}"
                        futures[executor.submit(check_adb_port, ip)] = ip

                    for future in as_completed(futures):
                        ip = futures[future]
                        try:
                            result = future.result()
                            if result:
                                found_devices.append(result)
                                console_print(f"  发现设备: {result}:5555", "SUCCESS")
                        except Exception:
                            pass

                if found_devices:
                    console_print(f"共发现 {len(found_devices)} 个设备，正在尝试连接...", "INFO")

                    # 尝试连接第一个找到的设备
                    for device_ip in found_devices:
                        wireless_addr = f"{device_ip}:5555"
                        console_print(f"正在连接 {wireless_addr}...", "INFO")

                        connect_result = subprocess.run(
                            ["adb", "connect", wireless_addr],
                            capture_output=True, text=True, timeout=10
                        )

                        if "connected" in connect_result.stdout.lower() or "already connected" in connect_result.stdout.lower():
                            console_print(f"✅ 无线连接成功: {wireless_addr}", "SUCCESS")
                            connected = True
                            break
                        else:
                            console_print(f"  连接 {wireless_addr} 失败", "INFO")
                else:
                    console_print("", "ERROR")
                    console_print("❌ 未在局域网内发现的无线设备", "ERROR")
                    console_print("", "ERROR")
                    console_print("请确保：", "ERROR")
                    console_print("  • 手机和电脑在同一网络", "ERROR")
                    console_print("  • 手机已启用 USB 调试", "ERROR")
                    console_print("  • 手机已通过 USB 线启用过无线调试模式（adb tcpip 5555）", "ERROR")
                    console_print("", "ERROR")
                    console_print("💡 首次使用建议：", "ERROR")
                    console_print("  1. 用 USB 线连接手机", "ERROR")
                    console_print("  2. 运行此脚本，它会自动启用无线模式", "ERROR")
                    console_print("  3. 之后拔掉 USB 线，设备将保持无线连接", "ERROR")
                    console_print("", "ERROR")
                    sys.exit(1)

            # 重新获取设备列表
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            device_list = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('List of devices'):
                    parts = line.split()
                    if parts:
                        device_list.append(parts[0])

            if not device_list:
                console_print("错误：连接后仍无法检测到设备", "ERROR")
                sys.exit(1)

        except subprocess.TimeoutExpired:
            console_print("操作超时，请检查：", "ERROR")
            console_print("  • USB 线是否正确连接", "ERROR")
            console_print("  • 手机是否已解锁", "ERROR")
            console_print("  • USB 调试是否已开启", "ERROR")
            logger.error("ADB 操作超时")
            sys.exit(1)
        except Exception as e:
            console_print("", "ERROR")
            console_print("❌ 自动发现失败", "ERROR")
            console_print("", "ERROR")
            console_print("🔍 请检查以下项目：", "ERROR")
            console_print("", "ERROR")
            console_print("1️⃣  USB 连接", "ERROR")
            console_print("   • USB 线是否插好", "ERROR")
            console_print("   • 手机是否有电", "ERROR")
            console_print("", "ERROR")
            console_print("2️⃣  手机设置", "ERROR")
            console_print("   • 设置 → 关于手机 → 连续点击「版本号」7次", "ERROR")
            console_print("   • 开发者选项 → USB 调试 → 开启", "ERROR")
            console_print("", "ERROR")
            console_print("3️⃣  手机授权", "ERROR")
            console_print("   • 连接后点击「允许」", "ERROR")
            console_print("", "ERROR")
            console_print("✅ 插上 USB 线后重新运行程序即可自动启用无线模式", "ERROR")
            console_print("", "ERROR")
            logger.error(f"自动发现异常: {e}", exc_info=True)
            sys.exit(1)

    device_id = device_list[0]
    device_wm_size = get_device_wm_size(device_id)  # 使用默认 show_window=True
    device_info = {"device_id": device_id, "device_wm_size": device_wm_size}
    logger.debug(f"设备信息: {device_info}")

    tmp_rollout_config = local_model_config

    # 控制台简洁显示
    console_print(f"任务: {task}")
    console_print(f"设备: {device_id} ({device_wm_size[0]}x{device_wm_size[1]})")
    console_print(f"模型: {local_model_config['model_config']['model_name']}")
    console_print("初始化...")
    l2_server = LocalServer(tmp_server_config)
    max_steps = tmp_rollout_config.get('max_steps', 400)
    wrap_automate_step_with_timing(l2_server, logger, max_steps)

    # 任务执行结果容器（用于线程间传递结果）
    task_result = {"done": False, "log": None, "error": None}

    def run_task_in_background():
        """在后台线程中执行任务"""
        try:
            total_start = time.time()
            return_log = evaluate_task_on_device(l2_server, device_info, task, tmp_rollout_config, reflush_app=True,reset_environment=False)
            total_time = time.time() - total_start

            task_result["done"] = True
            task_result["log"] = return_log
            task_result["total_time"] = total_time

            logger.info(f"任务执行返回: {return_log}")

            # 控制台显示统计
            console_print(f"完成！总耗时: {total_time:.1f}s，步数: {len(_step_times)}", "SUCCESS")
            if _step_times:
                avg_time = sum(_step_times) / len(_step_times)
                console_print(f"平均: {avg_time:.1f}s/步，最快: {min(_step_times):.1f}s，最慢: {max(_step_times):.1f}s")

            # 显示截图文件位置
            session_id = return_log.get("session_id", "unknown")
            image_dir = tmp_server_config.get("image_dir", "running_log/server_log/os-copilot-local-eval-logs/images")
            console_print(f"截图保存位置: {image_dir}")
            console_print(f"会话 ID: {session_id}")

            # 统计截图文件数量
            try:
                import glob
                screenshot_files = glob.glob(os.path.join(image_dir, f"{session_id}_*.jpeg")) + \
                                   glob.glob(os.path.join(image_dir, f"{session_id}_*.png"))
                if screenshot_files:
                    console_print(f"截图文件数量: {len(screenshot_files)} 个")
            except Exception:
                pass

            # 详细统计记录到文件
            logger.info("=" * 60)
            logger.info("每步耗时统计:")
            for i, step_time in enumerate(_step_times, 1):
                logger.info(f"  Step {i}: {step_time:.2f} 秒")
            if _step_times:
                logger.info(f"平均耗时: {avg_time:.2f} 秒，最大: {max(_step_times):.2f} 秒，最小: {min(_step_times):.2f} 秒")
            logger.info(f"日志文件保存于: {log_file}")

        except Exception as e:
            task_result["done"] = True
            task_result["error"] = e
            console_print(f"任务执行出错: {e}", "ERROR")
            logger.error(f"任务执行出错: {e}", exc_info=True)

    console_print("开始执行任务", "SUCCESS")

    # 获取 scrcpy client
    from copilot_front_end.scrcpy_connection_manager import get_scrcpy_manager
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id)

    # 启动后台任务线程
    task_thread = threading.Thread(target=lambda: evaluate_task_on_device(l2_server, device_info, task, tmp_rollout_config, reflush_app=True, reset_environment=False), daemon=True, name="TaskExecutionThread")
    task_thread.start()

    # 如果 client 有 video_window，在主线程运行 Qt 事件循环
    if client and hasattr(client, '_video_window') and client._video_window:
        logger.info("主线程启动 Qt 事件循环...")
        console_print("📺 实时预览窗口已启动")

        # 创建一个定时器来检查任务完成
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer, QCoreApplication

        def check_task_complete():
            """检查任务是否完成，完成后退出 Qt"""
            if not task_thread.is_alive():
                logger.info("任务完成，退出 Qt 事件循环")
                QCoreApplication.quit()
                return
            # 继续检查
            QTimer.singleShot(100, check_task_complete)

        # 启动检查定时器
        QTimer.singleShot(100, check_task_complete)

        # 运行 Qt 事件循环
        try:
            app = QApplication.instance()
            if app:
                app.exec()
                logger.info("Qt 事件循环已退出")
        except Exception as e:
            logger.error(f"Qt 事件循环出错: {e}", exc_info=True)

        # 等待任务线程结束
        task_thread.join(timeout=5.0)
    else:
        # 没有 video_window，直接等待任务完成
        task_thread.join()

    pass
