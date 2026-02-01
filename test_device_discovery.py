#!/usr/bin/env python3
"""
自动设备发现和 IP 获取测试脚本

用法：
1. 用 USB 线连接手机到电脑
2. 启用 USB 调试模式
3. 运行此脚本：python test_device_discovery.py
"""

import subprocess
import re
import sys

def run_command(cmd, timeout=10):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd.split(),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=isinstance(cmd, str)
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"

def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def main():
    print_section("步骤 1: 检查设备状态")

    # 1. 检查 ADB 设备
    code, stdout, stderr = run_command("adb devices")
    print(f"ADB 设备列表:\n{stdout}")

    if "List of devices attached" in stdout.strip().split('\n')[0]:
        devices = stdout.strip().split('\n')[1:]
        if not devices or not any(d.strip() for d in devices):
            print("❌ 未检测到设备")
            print("\n请确保：")
            print("1. USB 线已连接手机和电脑")
            print("2. 手机已启用「USB 调试」")
            print("3. 手动运行 'adb devices' 能看到设备")
            return
    else:
        print("❌ 无法检查 ADB 设备")
        return

    # 2. 解析设备列表
    usb_device = None
    for line in stdout.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith("List"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] != "List":
            if ':' not in parts[0]:  # USB 设备
                usb_device = parts[0]
                break

    if not usb_device:
        print("❌ 未检测到 USB 设备")
        return

    print(f"✅ 检测到 USB 设备: {usb_device}")

    # 3. 启用 TCP/IP
    print_section("步骤 2: 启用 TCP/IP 模式")
    print("命令: adb tcpip 5555")
    code, stdout, stderr = run_command(f"adb -s {usb_device} tcpip 5555", timeout=15)
    print(f"输出: {stdout}")
    if stderr:
        print(f"错误: {stderr}")

    if code != 0:
        print("❌ 启用 TCP/IP 失败")
        return

    print("✅ TCP/IP 模式已启用")

    # 4. 测试多种获取 IP 的方法
    print_section("步骤 3: 测试获取 IP 地址的方法")

    methods = [
        ("ip addr show wlan0", ["adb", "-s", usb_device, "shell", "ip", "addr", "show", "wlan0"]),
        ("ip addr show wifi0", ["adb", "-s", usb_device, "shell", "ip", "addr", "show", "wifi0"]),
        ("ip addr show wlan1", ["adb", "-s", usb_device, "shell", "ip", "addr", "show", "wlan1"]),
        ("ip route", ["adb", "-s", usb_device, "shell", "ip", "route"]),
        ("getprop dhcp.wlan0", ["adb", "-s", usb_device, "shell", "getprop", "dhcp.wlan0.ipaddress"]),
        ("getprop dhcp.wifi0", ["adb", "-s", usb_device, "shell", "getprop", "dhcp.wifi0.ipaddress"]),
        ("ifconfig wlan0", ["adb", "-s", usb_device, "shell", "ifconfig", "wlan0"]),
        ("settings get wifi_ip", ["adb", "-s", usb_device, "shell", "settings", "get", "global", "wifi_ip_address"]),
    ]

    ips_found = []

    for method_name, cmd in methods:
        print(f"\n▶ 方法: {method_name}")
        print(f"命令: {' '.join(cmd)}")
        code, stdout, stderr = run_command(cmd, timeout=5)

        if code == 0 and stdout:
            print(f"输出:\n{stdout}")
            # 提取 IP 地址
            found_ips = re.findall(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', stdout)
            for ip in found_ips:
                if not ip.startswith(('127.', '169.254.', '0.0.0.', '224.', '240.', '255.')):
                    if ip not in ips_found:
                        ips_found.append((ip, method_name))
                        print(f"✅ 找到 IP: {ip}")
        else:
            if stderr:
                print(f"错误: {stderr}")

    # 5. 显示所有找到的 IP
    print_section("步骤 4: IP 地址汇总")
    if ips_found:
        print(f"共找到 {len(ips_found)} 个可用 IP:")
        for ip, method in ips_found:
            print(f"  • {ip} (通过 {method_name})")
    else:
        print("❌ 未找到可用的 IP 地址")
        print("\n可能原因：")
        print("• 手机未连接 WiFi")
        print("• 网络接口名称不是 wlan0/wifi0")
        print("• 使用了其他网络接口（如以太网）")

    # 6. 验证 IP 可用性
    if ips_found:
        print_section("步骤 5: 验证 IP 可用性")
        working_ips = []

        for ip, _ in ips_found:
            print(f"\n▶ 测试 IP: {ip}:5555")
            code, stdout, stderr = run_command(f"adb connect {ip}:5555", timeout=10)

            if "connected" in stdout.lower() or "already connected" in stdout.lower():
                print(f"✅ {ip}:5555 可用!")
                working_ips.append(ip)
                # 断开测试连接
                run_command(f"adb disconnect {ip}:5555", timeout=5)
            else:
                print(f"✗ {ip}:5555 不可用")
                if stderr:
                    print(f"   错误: {stderr.strip()}")

        # 7. 最终结果
        print_section("步骤 6: 最终结果")
        if working_ips:
            print(f"✅ 发现 {len(working_ips)} 个可用的 IP:")
            for ip in working_ips:
                print(f"  • {ip}:5555")
            print("\n推荐使用第一个可用 IP")
        else:
            print("❌ 所有 IP 都无法连接")
            print("\n可能原因：")
            print("• 手机和电脑不在同一网络")
            print("• 防火墙阻止了 5555 端口")
            print("• ADB 无线连接有问题")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
