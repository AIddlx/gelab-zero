"""
scrcpy-py-ddlx 迁移测试脚本

验证从 ADB 到 scrcpy-py-ddlx 的迁移是否正常工作
"""

import sys
import time
import os
import logging

if "." not in sys.path:
    sys.path.append(".")

# 先导入所有需要的模块
from copilot_front_end.mobile_action_helper import (
    capture_screenshot_scrcpy,
    capture_screenshot_auto,
    get_device_wm_size_scrcpy,
    get_device_wm_size_auto,
    list_devices_scrcpy,
    list_devices_auto,
    USE_SCRCPY,
)

from copilot_front_end.pu_frontend_executor import (
    act_on_device_scrcpy,
    act_on_device_auto,
    USE_SCRCPY_FOR_ACTIONS,
)

from copilot_front_end.scrcpy_connection_manager import (
    ScrcpyConnectionManager,
    get_scrcpy_manager,
)

# 然后配置详细的日志
log_file = os.path.join(os.path.dirname(__file__), 'test_scrcpy_migration.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# 创建文件处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 创建控制台处理器（简化格式）
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)

# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)


def test_connection_manager():
    """测试连接管理器"""
    logger.info("=" * 60)
    logger.info("Test 1: ScrcpyConnectionManager")
    logger.info("=" * 60)

    manager = get_scrcpy_manager()

    # 列出设备
    devices = manager.list_connected_devices()
    logger.info(f"Connected devices: {devices}")

    if not devices:
        logger.info("No connected devices, trying to connect...")
        # 尝试从 list_devices_auto 获取
        all_devices = list_devices_auto()
        if all_devices:
            device_id = all_devices[0]
            logger.info(f"Trying to connect to device: {device_id}")
            client = manager.get_client(device_id)
            if client:
                logger.info(f"Connection successful! Device size: {client.device_size}")
                return device_id
        else:
            logger.error("No available devices")
            return None
    else:
        device_id = devices[0]
        logger.info(f"Using connected device: {device_id}")
        return device_id


def test_screenshot(device_id):
    """测试截图功能"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 2: Screenshot (scrcpy vs ADB)")
    logger.info("=" * 60)

    # 测试 scrcpy 截图
    logger.info("Capturing screenshot with scrcpy-py-ddlx...")
    start = time.time()
    try:
        path_scrcpy = capture_screenshot_scrcpy(device_id, "tmp_screenshot", "test_scrcpy.png")
        time_scrcpy = time.time() - start
        logger.info(f"[OK] scrcpy screenshot success: {path_scrcpy}")
        logger.info(f"    Time: {time_scrcpy * 1000:.1f} ms")
    except Exception as e:
        logger.error(f"[FAIL] scrcpy screenshot failed: {e}")
        path_scrcpy = None
        time_scrcpy = None

    # 测试自动选择截图
    logger.info("Capturing screenshot with auto-selection...")
    start = time.time()
    try:
        path_auto = capture_screenshot_auto(device_id, "tmp_screenshot", "test_auto.png")
        time_auto = time.time() - start
        logger.info(f"[OK] auto screenshot success: {path_auto}")
        logger.info(f"    Time: {time_auto * 1000:.1f} ms")
    except Exception as e:
        logger.error(f"[FAIL] auto screenshot failed: {e}")

    # 性能对比
    if path_scrcpy and time_scrcpy:
        logger.info(f"Performance: scrcpy took {time_scrcpy * 1000:.1f} ms")


def test_device_size(device_id):
    """测试获取设备尺寸"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 3: Device Size")
    logger.info("=" * 60)

    # scrcpy 方式
    size_scrcpy = get_device_wm_size_scrcpy(device_id)
    logger.info(f"scrcpy size: {size_scrcpy}")

    # 自动选择方式
    size_auto = get_device_wm_size_auto(device_id)
    logger.info(f"Auto size: {size_auto}")


def test_actions(device_id):
    """测试动作执行"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 4: Action Execution")
    logger.info("=" * 60)

    if not device_id:
        logger.error("No available device, skipping action tests")
        return

    # 获取设备尺寸
    wm_size = get_device_wm_size_auto(device_id)
    if not wm_size:
        wm_size = (1080, 2400)
    logger.info(f"Device size: {wm_size}")

    # 测试点击
    logger.info("")
    logger.info("Testing CLICK action...")
    try:
        click_action = {
            "action_type": "CLICK",
            "point": (500, 500)  # 屏幕中心
        }
        act_on_device_scrcpy(click_action, device_id, wm_size)
        logger.info("[OK] CLICK successful")
    except Exception as e:
        logger.error(f"[FAIL] CLICK failed: {e}")

    time.sleep(1)

    # 测试滑动
    logger.info("")
    logger.info("Testing SLIDE action...")
    try:
        slide_action = {
            "action_type": "SLIDE",
            "point1": (500, 1500),
            "point2": (500, 500),
            "duration": 0.5,
        }
        act_on_device_scrcpy(slide_action, device_id, wm_size)
        logger.info("[OK] SLIDE successful")
    except Exception as e:
        logger.error(f"[FAIL] SLIDE failed: {e}")

    time.sleep(1)

    # 测试返回键
    logger.info("")
    logger.info("Testing BACK action...")
    try:
        back_action = {"action_type": "BACK"}
        act_on_device_scrcpy(back_action, device_id, wm_size)
        logger.info("[OK] BACK successful")
    except Exception as e:
        logger.error(f"[FAIL] BACK failed: {e}")

    time.sleep(1)

    # 测试文本输入
    logger.info("")
    logger.info("Testing TYPE action...")
    try:
        type_action = {
            "action_type": "TYPE",
            "value": "test",
        }
        act_on_device_scrcpy(type_action, device_id, wm_size)
        logger.info("[OK] TYPE successful")
    except Exception as e:
        logger.error(f"[FAIL] TYPE failed: {e}")


def test_auto_fallback(device_id):
    """测试自动回退机制"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 5: Auto Fallback")
    logger.info("=" * 60)

    logger.info(f"USE_SCRCPY = {USE_SCRCPY}")
    logger.info(f"USE_SCRCPY_FOR_ACTIONS = {USE_SCRCPY_FOR_ACTIONS}")

    # 测试自动选择截图
    logger.info("")
    logger.info("Testing auto screenshot (fallback to ADB if scrcpy fails)...")
    try:
        path = capture_screenshot_auto(device_id, "tmp_screenshot", "test_fallback.png")
        logger.info(f"[OK] Screenshot success: {path}")
    except Exception as e:
        logger.error(f"[FAIL] Screenshot failed: {e}")


def main():
    """主测试函数"""
    logger.info("scrcpy-py-ddlx Migration Test")
    logger.info("=" * 60)

    try:
        # 测试 1: 连接管理器
        device_id = test_connection_manager()

        if not device_id:
            logger.error("No available devices, test terminated")
            return

        # 测试 2: 截图功能
        test_screenshot(device_id)

        # 测试 3: 设备尺寸
        test_device_size(device_id)

        # 测试 4: 动作执行
        test_actions(device_id)

        # 测试 5: 自动回退
        test_auto_fallback(device_id)

        logger.info("")
        logger.info("=" * 60)
        logger.info("All tests completed successfully")
        logger.info("=" * 60)
        logger.info(f"Log file saved to: {log_file}")

    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("Test failed with error:")
        logger.error(f"  {type(e).__name__}: {e}")
        logger.error("=" * 60)
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
