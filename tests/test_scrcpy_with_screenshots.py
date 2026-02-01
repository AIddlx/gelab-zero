"""
scrcpy-py-ddlx 截图验证测试

通过截图对比来验证动作是否真正执行
"""

import sys
import time
import os

if "." not in sys.path:
    sys.path.append(".")

from copilot_front_end.mobile_action_helper import (
    capture_screenshot_auto,
    get_device_wm_size_auto,
    list_devices_auto,
)
from copilot_front_end.pu_frontend_executor import act_on_device_scrcpy


def main():
    """主测试函数 - 使用截图验证动作执行"""

    # 列出设备
    devices = list_devices_auto()
    if not devices:
        print("没有找到设备")
        return

    device_id = devices[0]
    print(f"使用设备: {device_id}")

    # 获取设备尺寸
    wm_size = get_device_wm_size_auto(device_id)
    print(f"设备尺寸: {wm_size}")

    print("\n" + "=" * 60)
    print("截图验证测试 - 通过截图对比验证动作执行")
    print("=" * 60)
    print()

    # 创建截图目录
    screenshot_dir = "test_screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    # 初始截图
    print("步骤 1: 截取初始屏幕")
    initial_screenshot = capture_screenshot_auto(device_id, screenshot_dir, "01_initial.png")
    print(f"  初始截图保存到: {initial_screenshot}")
    time.sleep(1)

    # 按 HOME 键
    print("\n步骤 2: 按 HOME 键")
    home_action = {"action_type": "HOME"}
    act_on_device_scrcpy(home_action, device_id, wm_size)
    print("  HOME 键已执行")
    time.sleep(1)

    # 截图验证
    print("\n步骤 3: 截图验证 HOME 键效果")
    after_home_screenshot = capture_screenshot_auto(device_id, screenshot_dir, "02_after_home.png")
    print(f"  截图保存到: {after_home_screenshot}")
    time.sleep(1)

    # 打开计算器（使用模糊搜索）
    print("\n步骤 4: 打开计算器应用")
    awake_action = {
        "action_type": "AWAKE",
        "value": "计算器",  # 中文应用名，支持模糊搜索
    }
    act_on_device_scrcpy(awake_action, device_id, wm_size)
    print("  打开计算器命令已发送")
    time.sleep(2)  # 等待应用启动

    # 截图验证
    print("\n步骤 5: 截图验证计算器打开")
    after_calc_screenshot = capture_screenshot_auto(device_id, screenshot_dir, "03_after_calculator.png")
    print(f"  截图保存到: {after_calc_screenshot}")
    time.sleep(1)

    # 点击计算器按钮（点击数字 5）
    print("\n步骤 6: 点击计算器按钮（数字 5）")
    # 计算器按钮位置（根据屏幕尺寸估算）
    # 大多数计算器布局：数字 5 在屏幕中央稍偏下
    x = int(wm_size[0] * 0.5)  # 屏幕水平中心
    y = int(wm_size[1] * 0.6)  # 屏幕垂直 60% 位置
    click_action = {
        "action_type": "CLICK",
        "point": (x, y),
    }
    act_on_device_scrcpy(click_action, device_id, wm_size)
    print(f"  点击位置: ({x}, {y})")
    time.sleep(1)

    # 截图验证
    print("\n步骤 7: 截图验证点击效果")
    after_click_screenshot = capture_screenshot_auto(device_id, screenshot_dir, "04_after_click.png")
    print(f"  截图保存到: {after_click_screenshot}")
    time.sleep(1)

    # 按 BACK 键退出计算器
    print("\n步骤 8: 按 BACK 键退出计算器")
    back_action = {"action_type": "BACK"}
    act_on_device_scrcpy(back_action, device_id, wm_size)
    print("  BACK 键已执行")
    time.sleep(1)

    # 最终截图
    print("\n步骤 9: 最终截图")
    final_screenshot = capture_screenshot_auto(device_id, screenshot_dir, "05_final.png")
    print(f"  最终截图保存到: {final_screenshot}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print()
    print(f"所有截图保存在: {os.path.abspath(screenshot_dir)}")
    print()
    print("请对比以下截图来验证动作是否执行：")
    print("  1. 01_initial.png - 初始屏幕")
    print("  2. 02_after_home.png - 按 HOME 键后")
    print("  3. 03_after_calculator.png - 打开计算器后")
    print("  4. 04_after_click.png - 点击按钮后")
    print("  5. 05_final.png - 按 BACK 键后")
    print()
    print("如果计算器成功打开并点击了按钮，则说明 scrcpy 动作执行正常。")
    print()


if __name__ == "__main__":
    main()
