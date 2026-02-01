"""
设备连接诊断脚本
帮助诊断 Android 设备连接问题
"""

import subprocess
import sys

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"检查: {description}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ 命令超时")
        return False
    except FileNotFoundError:
        print("❌ 找不到命令，请确保 ADB 已安装")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    print("\n🔍 Android 设备连接诊断")
    print("="*60)

    # 1. 检查 ADB 版本
    run_command(["adb", "version"], "ADB 版本")

    # 2. 检查设备列表
    has_devices = run_command(["adb", "devices"], "已连接的设备")

    # 3. 检查 ADB 服务器状态
    run_command(["adb", "start-server"], "启动 ADB 服务器")

    # 4. 再次检查设备列表
    has_devices = run_command(["adb", "devices"], "已连接的设备（重启后）")

    if has_devices:
        lines = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout.strip().split('\n')
        device_count = sum(1 for line in lines if 'device' in line and not line.startswith('List'))
        print(f"\n✅ 检测到 {device_count} 个设备")
        return

    # 5. 没有设备，给出诊断建议
    print("\n" + "="*60)
    print("❌ 未检测到 Android 设备")
    print("="*60)
    print("\n可能的原因和解决方案：")
    print("\n1️⃣  USB 线连接问题")
    print("   - 更换 USB 线（使用原装或数据线，不要用充电线）")
    print("   - 更换 USB 接口（尝试 USB 2.0/3.0 不同接口）")
    print("   - 检查手机是否允许 USB 调试（连接时是否弹出授权提示）")
    print("\n2️⃣  手机设置问题")
    print("   - 进入「设置」→「关于手机」")
    print("   - 连续点击「版本号」7次，启用开发者模式")
    print("   - 返回「设置」→「系统」→「开发者选项」")
    print("   - 开启「USB 调试」")
    print("\n3️⃣  驱动问题")
    print("   - Windows: 设备管理器中查看是否有未识别的设备")
    print("   - 下载并安装手机厂商的驱动程序")
    print("\n4️⃣  ADB 授权问题")
    print("   - 连接 USB 后，手机上会弹出「允许 USB 调试」")
    print("   - 务必点击「允许」并勾选「始终允许」")
    print("\n" + "="*60)
    print("💡 快速测试连接:")
    print("="*60)
    print("1. 连接 USB 线")
    print("2. 在手机上允许 USB 调试")
    print("3. 运行: adb devices")
    print("4. 如果能看到设备，运行主程序:")
    print("   py examples\\run_single_task.py \"打开哔哩哔哩\"")
    print("\n")

if __name__ == "__main__":
    main()
