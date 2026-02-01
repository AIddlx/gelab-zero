"""
scrcpy-py-ddlx 可视化验证测试

使用有明显视觉反馈的动作来验证设备实际响应
"""

import sys
import time
import os
import logging

if "." not in sys.path:
    sys.path.append(".")

# 导入所需模块
from copilot_front_end.mobile_action_helper import (
    get_device_wm_size_auto,
    list_devices_auto,
)
from copilot_front_end.pu_frontend_executor import act_on_device_scrcpy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主测试函数 - 使用有明显视觉反馈的动作"""

    # 列出设备
    devices = list_devices_auto()
    if not devices:
        logger.error("没有找到设备")
        return

    device_id = devices[0]
    logger.info(f"使用设备: {device_id}")

    # 获取设备尺寸
    wm_size = get_device_wm_size_auto(device_id)
    logger.info(f"设备尺寸: {wm_size}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("可视化验证测试 - 请观察手机屏幕")
    logger.info("=" * 60)
    logger.info("每个动作之间会等待 2 秒，请观察手机屏幕变化")
    logger.info("")

    # 测试 1: HOME 键（最明显的效果 - 返回主屏幕）
    logger.info("测试 1/4: 按 HOME 键（应该返回主屏幕）")
    logger.info("  执行中...")
    try:
        home_action = {"action_type": "HOME"}
        act_on_device_scrcpy(home_action, device_id, wm_size)
        logger.info("  [OK] HOME 键执行成功")
    except Exception as e:
        logger.error(f"  [FAIL] HOME 键失败: {e}")
    time.sleep(2)

    # 测试 2: 打开设置应用（可见效果）
    logger.info("")
    logger.info("测试 2/4: 打开设置应用（应该出现设置界面）")
    logger.info("  执行中...")
    try:
        awake_action = {
            "action_type": "AWAKE",
            "value": "设置",  # 中文应用名
        }
        act_on_device_scrcpy(awake_action, device_id, wm_size)
        logger.info("  [OK] 打开设置执行成功")
    except Exception as e:
        logger.error(f"  [FAIL] 打开设置失败: {e}")
    time.sleep(2)

    # 测试 3: 向下滚动（在设置界面中）
    logger.info("")
    logger.info("测试 3/4: 向下滚动（设置内容应该向上移动）")
    logger.info("  执行中...")
    try:
        # 计算滚动位置（屏幕右侧用于滚动）
        x = int(wm_size[0] * 0.8)  # 屏幕右侧 80% 位置
        y_center = int(wm_size[1] * 0.5)  # 垂直中心
        scroll_distance = int(wm_size[1] * 0.3)  # 滚动 30% 屏幕高度

        scroll_action = {
            "action_type": "SCROLL",
            "point": (x, y_center),
            "direction": "down",
        }
        act_on_device_scrcpy(scroll_action, device_id, wm_size)
        logger.info("  [OK] 滚动执行成功")
    except Exception as e:
        logger.error(f"  [FAIL] 滚动失败: {e}")
    time.sleep(2)

    # 测试 4: 返回键（应该退出设置）
    logger.info("")
    logger.info("测试 4/4: 按 BACK 键（应该退出设置）")
    logger.info("  执行中...")
    try:
        back_action = {"action_type": "BACK"}
        act_on_device_scrcpy(back_action, device_id, wm_size)
        logger.info("  [OK] BACK 键执行成功")
    except Exception as e:
        logger.error(f"  [FAIL] BACK 键失败: {e}")
    time.sleep(2)

    logger.info("")
    logger.info("=" * 60)
    logger.info("测试完成！")
    logger.info("=" * 60)
    logger.info("")
    logger.info("如果您看到手机屏幕有以下变化，则测试成功：")
    logger.info("  1. 按 HOME 键后返回主屏幕")
    logger.info("  2. 打开设置后出现设置界面")
    logger.info("  3. 滚动后设置内容向上移动")
    logger.info("  4. 按 BACK 键后退出设置")
    logger.info("")


if __name__ == "__main__":
    main()
