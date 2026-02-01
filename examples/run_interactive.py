"""
多轮对话交互式 Android 自动化脚本

功能：
- 持续对话，可以输入多个任务
- 保持 scrcpy 连接和设备状态
- 支持命令：/quit 退出, /clear 清屏, /devices 列出设备
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime
import signal  # 添加信号处理

if "." not in sys.path:
    sys.path.append(".")

# 先设置 scrcpy 日志级别（在导入之前）
import logging
logging.getLogger('scrcpy_py_ddlx').setLevel(logging.ERROR)
logging.getLogger('scrcpy_py_ddlx.core.demuxer').setLevel(logging.ERROR)
logging.getLogger('scrcpy_py_ddlx.core.demuxer.video').setLevel(logging.ERROR)

from copilot_agent_client.pu_client import evaluate_task_on_device
from copilot_front_end.mobile_action_helper import list_devices, get_device_wm_size
from copilot_front_end.scrcpy_connection_manager import get_scrcpy_manager
from copilot_agent_server.local_server import LocalServer

# ===== 日志配置 =====
def setup_logging(log_dir="running_log/logs"):
    """配置日志系统"""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"run_interactive_{timestamp}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 控制台处理器 - 只显示重要信息
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)

    # 过滤第三方库日志
    for lib in ['PIL', 'PIL.PngImagePlugin', 'httpcore', 'httpx', 'openai', 'openai._base_client',
                'scrcpy_py_ddlx', 'scrcpy_py_ddlx.core', 'scrcpy_py_ddlx.core.demuxer']:
        logging.getLogger(lib).setLevel(logging.ERROR)

    logging.info(f"日志文件: {log_file}")
    return log_file, logger


# ===== 配置 =====
server_config = {
    "log_dir": "running_log/server_log/os-copilot-local-eval-logs/traces",
    "image_dir": "running_log/server_log/os-copilot-local-eval-logs/images",
    "debug": False
}

model_config = {
    "task_type": "parser_0922_summary",
    "model_config": {
        "model_name": "gelab-zero-4b-preview",
        "model_provider": "local",
        "args": {
            "temperature": 0.1,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "max_tokens": 40960,
        },
        "image_preprocess": {
            "is_resize": True,
            "target_image_size": [728, 728]
        }
    },
    "max_steps": 400,
    "delay_after_capture": 2,
    "debug": False,
}


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


def print_banner():
    """打印欢迎横幅"""
    print("\n" + "=" * 60)
    print("  Android 自动化交互式对话模式")
    print("=" * 60)
    print("命令:")
    print("  /quit  - 退出程序")
    print("  /clear - 清屏")
    print("  /devices - 列出连接的设备")
    print("  直接输入任务描述即可执行")
    print("=" * 60 + "\n")


def auto_discover_device(logger):
    """
    自动发现并连接设备

    策略1: 检查 USB 设备，自动启用无线模式
    策略2: 扫描局域网寻找无线 ADB 设备

    Returns:
        list: 设备列表，失败返回空列表
    """
    import subprocess
    import re
    import socket
    from concurrent.futures import ThreadPoolExecutor, as_completed

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
                return []

            console_print("✅ TCP/IP 模式已启用", "INFO")

            # 步骤2: 从设备获取 IP 地址
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
                return []

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
                return []

        # 策略2: 如果没有 USB，扫描局域网寻找 ADB 设备
        if not connected:
            console_print("未检测到 USB 设备，正在扫描局域网...", "INFO")

            # 获取本机 IP 和网段
            local_ip = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(2)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "192.168.1.1"

            console_print(f"本机 IP: {local_ip}", "INFO")

            # 提取网段
            ip_parts = local_ip.split('.')
            network_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"

            console_print(f"正在扫描网段 {network_prefix}.0/24 中的无线设备...", "INFO")

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
                return []

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
            return []

        return device_list

    except subprocess.TimeoutExpired:
        console_print("操作超时，请检查：", "ERROR")
        console_print("  • USB 线是否正确连接", "ERROR")
        console_print("  • 手机是否已解锁", "ERROR")
        console_print("  • USB 调试是否已开启", "ERROR")
        logger.error("ADB 操作超时")
        return []
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
        return []


def execute_task(device_info, task, l2_server, model_config, result_container=None):
    """执行单个任务（在线程中运行）"""
    device_id = device_info["device_id"]
    print(f"\n[执行中] {task}", flush=True)

    try:
        start_time = time.time()
        return_log = evaluate_task_on_device(
            l2_server,
            device_info,
            task,
            model_config,
            reflush_app=False  # 不重启应用，保持状态
        )
        elapsed = time.time() - start_time

        print(f"[完成] 耗时: {elapsed:.1f}s", flush=True)
        if result_container is not None:
            result_container["done"] = True
            result_container["log"] = return_log
        return return_log

    except Exception as e:
        print(f"[错误] {e}", flush=True)
        logging.error(f"任务执行出错: {e}", exc_info=True)
        if result_container is not None:
            result_container["done"] = True
            result_container["error"] = e
        return None


def main():
    """主函数"""
    # 设置 Ctrl+C 处理（在 main 函数开始时）
    def signal_handler(sig, frame):
        print("\n[退出] Ctrl+C 检测到")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    log_file, logger = setup_logging()
    print_banner()

    # 初始化服务器
    print("[初始化] 正在初始化本地服务器...")
    l2_server = LocalServer(server_config)

    # 获取设备列表
    device_list = list_devices()

    # 如果没有检测到设备，尝试自动发现和连接
    if not device_list:
        console_print("未检测到已连接设备，尝试自动发现...", "WARN")
        device_list = auto_discover_device(logger)
        if not device_list:
            return

    device_id = device_list[0]

    print(f"[调试1] 设备ID: {device_id}", flush=True)

    # 不使用 get_device_wm_size，直接用默认尺寸或 ADB 获取
    # 使用 subprocess 直接调用 adb 获取屏幕尺寸
    import subprocess
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "wm", "size"],
            capture_output=True, text=True, timeout=5
        )
        # 解析输出: Physical size: 1080x2400
        size_line = result.stdout.strip()
        if "x" in size_line:
            size_part = size_line.split()[-1]
            width, height = map(int, size_part.split("x"))
            device_wm_size = (width, height)
        else:
            device_wm_size = (1080, 2400)  # 默认值
    except Exception as e:
        print(f"[警告] 无法获取屏幕尺寸，使用默认值: {e}", flush=True)
        device_wm_size = (1080, 2400)  # 默认值

    print(f"[调试2] 屏幕尺寸: {device_wm_size}", flush=True)

    device_info = {
        "device_id": device_id,
        "device_wm_size": device_wm_size
    }

    print(f"[设备] {device_id} ({device_wm_size[0]}x{device_wm_size[1]})")
    print(f"[模型] {model_config['model_config']['model_name']}")
    print("[就绪] 输入任务开始对话\n")
    print("使用命令行模式（无预览窗口）\n", flush=True)

    # 简单的命令行循环
    while True:
        try:
            user_input = input(">>> ").strip()
            print(f"[DEBUG] 收到: {repr(user_input)}", flush=True)

            if not user_input:
                continue

            if user_input.lower() in ['/quit', '/exit', '/q']:
                print("[退出]")
                break

            elif user_input.lower() == '/clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                print_banner()
                continue

            elif user_input.lower() == '/devices':
                devices = list_devices()
                print(f"\n[设备列表] 共 {len(devices)} 台:")
                for i, dev in enumerate(devices, 1):
                    print(f"  {i}. {dev}")
                print()
                continue

            # 执行任务
            print(f"[开始执行] {user_input}", flush=True)
            result = execute_task(device_info, user_input, l2_server, model_config)
            if result:
                print(f"[执行完成]", flush=True)

        except KeyboardInterrupt:
            print("\n[退出]")
            break
        except EOFError:
            break
        except Exception as e:
            print(f"[错误] {e}", flush=True)


if __name__ == "__main__":
    main()
