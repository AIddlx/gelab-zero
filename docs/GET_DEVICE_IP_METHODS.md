# 获取手机无线 IP 方法总结

## 经过验证的最佳方法

### 方法1: ip addr show wlan0（推荐）✅

```bash
adb shell "ip addr show wlan0"
# 输出: inet 192.168.5.36/24 brd 192.168.5.255 scope global wlan0
# 提取正则: inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})
# 结果: 192.168.5.36
```

**优点**：
- ✅ 简单直接，一条命令搞定
- ✅ 适用于所有现代 Android 设备
- ✅ 输出格式稳定，易于解析
- ✅ 返回的是全局 IP 地址（非临时）

### 方法2: ip route（备选）✅

```bash
adb shell "ip route"
# 输出: 192.168.5.0/24 dev wlan0 src 192.168.5.36
# 提取正则: src\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})
# 结果: 192.168.5.36
```

### 失败的方法

| 方法 | 命令 | 结果 |
|------|------|------|
| getprop | `adb shell "getprop dhcp.wlan0.ipaddress"` | null ❌ |
| settings | `adb shell "settings get global wifi_ip_address"` | null ❌ |

## Python 代码实现

### 基础版本

```python
import subprocess
import re

def get_device_ip():
    """获取手机无线 IP 地址"""
    result = subprocess.run(
        ["adb", "shell", "ip addr show wlan0"],
        capture_output=True, text=True, timeout=5
    )

    match = re.search(r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', result.stdout)
    if match:
        return match.group(1)
    return None

# 使用
ip = get_device_ip()
print(f"设备 IP: {ip}")
```

### 多网卡版本（推荐）

```python
def get_device_ip_with_validation():
    """获取并验证设备 IP"""
    interfaces = ["wlan0", "wlan1", "eth0", "eth1"]
    candidate_ips = []

    # 收集候选 IP
    for interface in interfaces:
        result = subprocess.run(
            ["adb", "shell", f"ip addr show {interface}"],
            capture_output=True, text=True, timeout=5
        )

        for match in re.finditer(r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', result.stdout):
            ip = match.group(1)
            # 过滤特殊地址
            if not ip.startswith(('127.', '169.254.', '0.0.0.', 'fe80:', '224.', '240.')):
                candidate_ips.append((ip, interface))

    # 验证 IP 可用性
    for ip, interface in candidate_ips:
        # 方法1: 尝试 ping
        ping_result = subprocess.run(
            ["ping", "-n", "1", "-W", "2", ip],
            capture_output=True, timeout=5
        )
        if ping_result.returncode == 0:
            return ip

        # 方法2: 尝试连接 ADB
        connect_result = subprocess.run(
            ["adb", "connect", f"{ip}:5555"],
            capture_output=True, text=True, timeout=10
        )
        if "connected" in connect_result.stdout.lower():
            return ip

    return None
```

## 关键过滤规则

需要过滤的地址类型：

| 类型 | 示例 | 说明 |
|------|------|------|
| 本地回环 | 127.0.0.1 | 设备自身 |
| 链路本地 | 169.254.x.x | 自动配置地址 |
| 特殊用途 | 0.0.0.x, 224.x, 240.x | 组播/特殊用途 |
| IPv6 链路本地 | fe80::/64 | IPv6 本地地址 |

## 实际测试结果

设备：Android 手机通过 WiFi 连接

| 方法 | 命令 | 结果 |
|------|------|------|
| **ip addr show wlan0** | `adb shell "ip addr show wlan0"` | ✅ **192.168.5.36** |
| ip route | `adb shell "ip route"` | ✅ 192.168.5.36 |
| getprop | `adb shell "getprop dhcp.wlan0.ipaddress"` | ❌ null |
| settings | `adb shell "settings get global wifi_ip_address"` | ❌ null |

## 总结

**推荐方案**：
```python
# 一行命令搞定
adb shell "ip addr show wlan0" | grep -oP 'inet \K[\d.]+'
```

**提取正则**：`inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3})`

**关键过滤**：排除 127.x, 169.254.x, 0.0.0.x, fe80::, 224.x, 240.x

---

## 完整自动发现流程

### 场景说明

当 `adb devices` 显示为空时，有三种可能的场景：

1. **有 USB 连接**：通过 USB 获取 IP 后自动启用无线
2. **无 USB，设备已启用无线调试**：扫描局域网寻找设备
3. **完全未启用**：需要先用 USB 启用一次

### 自动发现策略

#### 策略1: USB 自动启用无线（首选）

```python
import subprocess
import re

# 1. 检查 USB 设备
result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
usb_device = None

for line in result.stdout.strip().split('\n'):
    if 'device' in line and ':' not in line.split()[0]:  # USB 设备不含冒号
        usb_device = line.split()[0]
        break

if usb_device:
    # 2. 启用 TCP/IP 模式
    subprocess.run(["adb", "-s", usb_device, "tcpip", "5555"], timeout=15)

    # 3. 获取 IP 地址
    interfaces = ["wlan0", "wifi0", "wlan1", "eth0"]
    device_ip = None

    for interface in interfaces:
        result = subprocess.run(
            ["adb", "-s", usb_device, "shell", "ip", "addr", "show", interface],
            capture_output=True, text=True
        )
        match = re.search(r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', result.stdout)
        if match:
            device_ip = match.group(1)
            break

    # 4. 建立无线连接
    if device_ip:
        subprocess.run(["adb", "connect", f"{device_ip}:5555"])
        print(f"✅ 无线连接成功: {device_ip}:5555")
```

#### 策略2: 局域网扫描（无 USB 时）

```python
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# 1. 获取本机网段
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
local_ip = s.getsockname()[0]
s.close()

network_prefix = '.'.join(local_ip.split('.')[:3])

# 2. 扫描网段内所有 IP 的 5555 端口
found_devices = []

with ThreadPoolExecutor(max_workers=50) as executor:
    futures = {}
    for i in range(1, 255):
        ip = f"{network_prefix}.{i}"
        futures[executor.submit(check_adb_port, ip)] = ip

    for future in as_completed(futures):
        result = future.result()
        if result:
            found_devices.append(result)
            print(f"发现设备: {result}:5555")

# 3. 尝试连接找到的设备
for device_ip in found_devices:
    result = subprocess.run(
        ["adb", "connect", f"{device_ip}:5555"],
        capture_output=True, text=True
    )
    if "connected" in result.stdout.lower():
        print(f"✅ 连接成功: {device_ip}:5555")
        break
```

### 实际运行示例

```
⚠️  未检测到已连接设备，尝试自动发现...
本机 IP: 192.168.5.2
正在扫描网段 192.168.5.0/24 中的无线设备...
正在扫描设备（这可能需要 10-30 秒）...
✅ 发现设备: 192.168.5.36:5555
共发现 1 个设备，正在尝试连接...
正在连接 192.168.5.36:5555...
✅ 无线连接成功: 192.168.5.36:5555
```

### 流程图

```
启动脚本
    ↓
检查设备列表
    ↓
为空？
    ↓ 是
检查 USB 设备 ──→ 有 USB ──→ 启用 TCP/IP → 获取 IP → 无线连接 ✅
    ↓ 无 USB
扫描局域网 5555 端口
    ↓
找到设备？
    ↓ 是
adb connect → 连接成功 ✅
    ↓ 否
提示用户连接 USB 或检查网络
```

### 关键要点

1. **首次使用必须用 USB**：Android 需要通过 USB 先启用无线调试模式
2. **局域网扫描需要设备已启用无线调试**：端口 5555 必须开放
3. **多线程扫描加速**：50 线程并发，10-30 秒完成扫描
4. **自动切换**：USB 启用后可拔除，自动保持无线连接
