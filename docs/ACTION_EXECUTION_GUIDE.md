# Android 动作执行系统详细文档

## 目录
1. [系统概述](#系统概述)
2. [核心架构](#核心架构)
3. [动作类型定义](#动作类型定义)
4. [坐标系统](#坐标系统)
5. [ADB 命令实现](#adb-命令实现)
6. [YADB 工具](#yadb-工具)
7. [屏幕方向检测](#屏幕方向检测)
8. [应用启动机制](#应用启动机制)
9. [使用示例](#使用示例)
10. [错误处理](#错误处理)

---

## 系统概述

本项目实现了一个完整的 Android 设备自动化控制系统，通过 ADB（Android Debug Bridge）和自定义的 YADB 工具来执行各种设备操作。系统支持多种动作类型，包括点击、长按、滑动、输入文本、应用启动等。

### 核心文件
- `C:\Project\IDEA\gelab-zero\copilot_front_end\pu_frontend_executor.py` - 主要的动作执行器
- `C:\Project\IDEA\gelab-zero\copilot_front_end\mobile_action_helper.py` - 设备管理辅助工具
- `C:\Project\IDEA\gelab-zero\copilot_front_end\package_map.py` - 应用包名映射
- `C:\Project\IDEA\gelab-zero\copilot_tools\action_tools.py` - 动作类型定义和验证

---

## 核心架构

### 动作执行流程

```
用户指令 → 动作解析 → 坐标转换 → ADB命令生成 → 设备执行 → 结果返回
```

### 主要组件

#### 1. `pu_frontend_executor.py` - 前端动作执行器
这是核心执行模块，包含：
- **动作解析函数**：将不同格式的动作转换为统一的前端动作格式
- **动作执行函数**：`act_on_device()` - 实际执行所有类型的设备操作
- **坐标转换函数**：处理归一化坐标到实际像素的转换
- **屏幕方向检测**：自动检测设备横竖屏状态

#### 2. `mobile_action_helper.py` - 移动设备辅助工具
提供设备管理功能：
- 设备列表获取：`list_devices()`
- 屏幕尺寸获取：`get_device_wm_size()`
- 屏幕开关控制：`open_screen()`, `press_power_key()`
- 截图功能：`capture_screenshot()`
- YADB 工具初始化：`init_device()`

#### 3. `BaseMoboleActionHelper` 类
提供高级交互接口：
```python
class BaseMoboleActionHelper:
    def __init__(self, device_id=None)
    def step_interaction(self, action, capture_duration=0.5, image_full_path=None, user_comment=None)
```

---

## 动作类型定义

系统支持以下 13 种动作类型（定义在 `action_tools.py`）：

### 1. **CLICK** - 点击
- **参数**：`point=(x, y)` - 归一化坐标 (0-1000)
- **用途**：点击屏幕上的某个位置
- **示例**：
```python
{
    "action_type": "CLICK",
    "point": (500, 500)  # 屏幕中心
}
```

### 2. **LONGPRESS** - 长按
- **参数**：
  - `point=(x, y)` - 归一化坐标
  - `duration=float` - 持续时间（秒）
- **用途**：长按屏幕上的某个位置
- **示例**：
```python
{
    "action_type": "LONGPRESS",
    "point": (500, 500),
    "duration": 2.0  # 长按2秒
}
```

### 3. **TYPE** - 文本输入
- **参数**：
  - `value=str` - 要输入的文本
  - `point=(x, y)` - (可选)输入框坐标
  - `keyboard_exists=bool` - (可选)键盘是否已显示，默认True
- **用途**：输入文本内容
- **示例**：
```python
{
    "action_type": "TYPE",
    "value": "Hello World",
    "point": (500, 800),
    "keyboard_exists": False  # 需要先点击唤起键盘
}
```

### 4. **SCROLL** - 滚动
- **参数**：
  - `point=(x, y)` - 滚动起点
  - `direction=str` - 方向："up"|"down"|"left"|"right"
- **用途**：屏幕滚动操作
- **示例**：
```python
{
    "action_type": "SCROLL",
    "point": (500, 500),
    "direction": "down"  # 向下滚动
}
```

### 5. **SLIDE** - 滑动
- **参数**：
  - `point1=(x1, y1)` - 起点坐标
  - `point2=(x2, y2)` - 终点坐标
  - `duration=float` - (可选)滑动时长，默认1.5秒
- **用途**：自定义路径滑动
- **示例**：
```python
{
    "action_type": "SLIDE",
    "point1": (500, 800),
    "point2": (500, 200),
    "duration": 1.0
}
```

### 6. **AWAKE** - 应用启动
- **参数**：`value=str` - 应用名称
- **用途**：启动指定应用
- **示例**：
```python
{
    "action_type": "AWAKE",
    "value": "微信"  # 会从package_map中查找包名
}
```

### 7. **BACK** - 返回键
- **参数**：无
- **用途**：模拟返回键
- **示例**：
```python
{"action_type": "BACK"}
```

### 8. **HOME** - 主页键
- **参数**：无
- **用途**：模拟主页键，返回桌面
- **示例**：
```python
{"action_type": "HOME"}
```

### 9. **HOT_KEY** - 热键
- **参数**：`key=str` - 按键名称
- **支持的按键**：
  - `volume_up` - 音量加
  - `volume_down` - 音量减
  - `power` - 电源键
  - `home` - 主页键
  - `back` - 返回键
  - `menu` - 菜单键
- **示例**：
```python
{
    "action_type": "HOT_KEY",
    "key": "volume_up"
}
```

### 10. **WAIT** - 等待
- **参数**：`seconds=float` - 等待秒数
- **用途**：暂停执行
- **示例**：
```python
{
    "action_type": "WAIT",
    "seconds": 2.5
}
```

### 11. **COMPLETE** - 任务完成
- **参数**：无
- **用途**：标记任务成功完成
- **示例**：
```python
{"action_type": "COMPLETE"}
```

### 12. **ABORT** - 任务中止
- **参数**：无
- **用途**：标记任务中止
- **示例**：
```python
{"action_type": "ABORT"}
```

### 13. **INFO** - 信息请求
- **参数**：`value=str` - 要询问的信息
- **用途**：向用户请求信息
- **示例**：
```python
{
    "action_type": "INFO",
    "value": "请输入验证码"
}
```

---

## 坐标系统

### 归一化坐标系统（1000x1000）

项目使用 **0-1000** 的归一化坐标系统，具有以下优势：
- **设备无关**：同一动作可在不同分辨率的设备上执行
- **简化计算**：无需关注具体设备分辨率
- **精度适中**：1000级精度足以应对大部分场景

### 坐标转换逻辑

#### 1. 归一化坐标 → 固定点（1000基准）

```python
def _convert_normalized_point_to_fixed_point(point):
    """
    将 0.0-1.0 的归一化坐标转换为 0-1000 的固定点坐标

    Args:
        point: (x, y) 其中 x, y 在 [0.0, 1.0] 范围内

    Returns:
        (fixed_x, fixed_y) 其中坐标在 [0, 1000] 范围内
    """
    x, y = point
    assert type(x) == float and type(y) == float
    assert 0.0 <= float(x) <= 1.0
    assert 0.0 <= float(y) <= 1.0

    fixed_x = int(float(x) * 1000)
    fixed_y = int(float(y) * 1000)
    return (fixed_x, fixed_y)
```

**示例**：
- 输入：`(0.5, 0.5)` → 输出：`(500, 500)`
- 输入：`(0.123, 0.456)` → 输出：`(123, 456)`

#### 2. 固定点 → 实际像素坐标

```python
def _convert_point_to_realworld_point(point, wm_size):
    """
    将 0-1000 的固定点坐标转换为设备实际像素坐标

    Args:
        point: (x, y) 其中坐标在 [0, 1000] 范围内
        wm_size: (width, height) 设备实际分辨率

    Returns:
        (real_x, real_y) 设备像素坐标
    """
    x, y = point
    real_x = (float(x) / 1000) * wm_size[0]
    real_y = (float(y) / 1000) * wm_size[1]
    return (real_x, real_y)
```

**示例**（设备分辨率 1080x2400）：
- 输入：`(500, 500)` → 输出：`(540.0, 1200.0)`
- 输入：`(1000, 1000)` → 输出：`(1080.0, 2400.0)`

#### 3. 完整转换流程

```
归一化(0.0-1.0) → 固定点(0-1000) → 实际像素(设备分辨率)
   (0.5, 0.5)  →   (500, 500)   →   (540, 1200) [1080x2400设备]
```

---

## ADB 命令实现

### 设备命令前缀

```python
if device_id is None:
    adb_command = "adb"
else:
    adb_command = f"adb -s {device_id}"
```

### 各动作的 ADB 命令详解

#### 1. CLICK - 点击

```python
# ADB 命令
cmd = f"adb -s {device_id} shell input tap {x} {y}"

# 实际示例
adb -s emulator-5554 shell input tap 540 1200
```

**说明**：
- `input tap` 是 Android 标准输入命令
- `{x} {y}` 是实际像素坐标
- 支持屏幕方向自动调整

#### 2. LONGPRESS - 长按

```python
# 使用 YADB 工具（推荐）
cmd = f"adb -s {device_id} shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -touch {x} {y} {int(duration * 1000)}"

# 实际示例（长按2秒）
adb -s emulator-5554 shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -touch 540 1200 2000
```

**说明**：
- 使用 YADB 工具实现精确的长按控制
- 最后一个参数是持续时间（毫秒）
- 标准 ADB `input swipe` 命令无法精确控制长按时长

#### 3. TYPE - 文本输入

```python
# 使用 YADB 工具（支持中文和特殊字符）
cmd = f"adb -s {device_id} shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -keyboard '{preprocess_text_for_adb(value)}'"

# 实际示例
adb -s emulator-5554 shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -keyboard '你好，世界'
```

**文本预处理**：
```python
def preprocess_text_for_adb(text):
    """转义特殊字符"""
    text = text.replace("\n", " ").replace("\t", " ")
    text = text.replace(" ", "\\ ")
    return text
```

**键盘处理逻辑**：
```python
if not keyboard_exists:
    if "point" in frontend_action:
        # 先点击输入框唤起键盘
        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)
        cmd = f"adb -s {device_id} shell input tap {x} {y}"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)
        time.sleep(1)  # 等待键盘弹出
```

**为什么不使用标准 ADB input text**：
- 标准 `input text` 不支持中文
- 不支持很多特殊字符
- 需要复杂的转义处理

#### 4. SCROLL - 滚动

```python
# 计算滑动距离
deltax = int(0.3 * wm_size[0])  # 横向滑动屏幕宽度的30%
deltay = int(0.3 * wm_size[1])  # 纵向滑动屏幕高度的30%

# 根据方向确定终点
if direction == "down":
    x1, y1 = x, y
    x2, y2 = x, y - deltay
elif direction == "up":
    x1, y1 = x, y
    x2, y2 = x, y + deltay
# ... 其他方向

# ADB 命令
cmd = f"adb -s {device_id} shell input swipe {x1} {y1} {x2} {y2} 1200"

# 实际示例（向下滚动）
adb -s emulator-5554 shell input swipe 540 1200 540 360 1200
```

**参数说明**：
- 滑动距离固定为屏幕尺寸的 30%
- 最后一个参数 `1200` 是滑动持续时间（毫秒）

#### 5. SLIDE - 自定义滑动

```python
cmd = f"adb -s {device_id} shell input swipe {x1} {y1} {x2} {y2} {int(duration * 1000)}"

# 实际示例（从底部滑到顶部，持续1秒）
adb -s emulator-5554 shell input swipe 540 2160 540 240 1000
```

#### 6. AWAKE - 应用启动

```python
# 1. 先强制停止应用（可选）
if reflush_app:
    cmd = f"adb -s {device_id} shell am force-stop {package_name}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)
    time.sleep(1)

# 2. 使用 monkey 命令启动应用
cmd = f"adb -s {device_id} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
subprocess.run(cmd, shell=True, capture_output=True, text=True)

# 实际示例（启动微信）
adb -s emulator-5554 shell am force-stop com.tencent.mm
adb -s emulator-5554 shell monkey -p com.tencent.mm -c android.intent.category.LAUNCHER 1
```

**为什么使用 monkey 而不是 am start**：
- `monkey` 命令更可靠，能模拟真实用户点击图标
- 不需要知道具体的 Activity 名称
- 自动处理启动类别和权限

**包名查找**：
```python
# 从 package_map.py 中查找
package_name = find_package_name("微信")  # 返回 "com.tencent.mm"

# 支持模糊匹配
package_name = find_package_name("wechat")  # 通过相似度匹配找到 "微信"
```

#### 7. BACK - 返回键

```python
cmd = f"adb -s {device_id} shell input keyevent 4"

# 实际示例
adb -s emulator-5554 shell input keyevent 4
```

**KeyEvent 对照表**：
- `3` - HOME 键
- `4` - BACK 键
- `24` - 音量加
- `25` - 音量减
- `26` - 电源键
- `82` - 菜单键

#### 8. HOME - 主页键

```python
cmd = f"adb -s {device_id} shell input keyevent 3"

# 实际示例
adb -s emulator-5554 shell input keyevent 3
```

#### 9. HOT_KEY - 热键

```python
key_event_map = {
    "volume_up": 24,
    "volume_down": 25,
    "power": 26,
    "home": 3,
    "back": 4,
    "menu": 82,
}

cmd = f"adb -s {device_id} shell input keyevent {key_event}"

# 实际示例（音量加）
adb -s emulator-5554 shell input keyevent 24
```

#### 10. WAIT - 等待

```python
time.sleep(seconds)

# 不执行 ADB 命令，直接在 Python 层等待
```

---

## YADB 工具

### 什么是 YADB

YADB 是一个增强版的 ADB 工具，专门用于解决标准 ADB 在以下场景的不足：
1. **精确的触摸时长控制**（长按）
2. **中文和特殊字符输入**
3. **更复杂的触摸操作**

### YADB 的优势

#### 1. 精确长按控制

**标准 ADB 的局限**：
```bash
# 标准方法：使用 swipe 模拟长按，但不精确
adb shell input swipe 500 500 500 500 2000  # 理论上长按2秒，但实际不可靠
```

**YADB 的优势**：
```bash
# YADB：精确控制触摸时长
adb shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -touch 500 500 2000
```

#### 2. 中文输入支持

**标准 ADB 的局限**：
```bash
# 标准 input text 不支持中文
adb shell input text "你好"  # 只能输入英文
```

**YADB 的优势**：
```bash
# YADB：完美支持中文
adb shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -keyboard "你好，世界"
```

### YADB 初始化

```python
def init_device(device_id, print_command=False):
    """
    初始化设备，确保 YADB 已安装
    """
    adb_command = _get_adb_command(device_id)

    # 检查 YADB 是否已安装（通过 MD5 校验）
    command = f"{adb_command} shell md5sum /data/local/tmp/yadb"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # MD5: 29a0cd3b3adea92350dd5a25594593df
    if "29a0cd3b3adea92350dd5a25594593df" not in result.stdout:
        # YADB 未安装，推送到设备
        command = f"{adb_command} push yadb /data/local/tmp"
        logger.info(f"YADB not installed, installing on device {device_id}...")
        subprocess.run(command, shell=True, capture_output=True, text=True)
    else:
        logger.debug(f"YADB already installed on device {device_id}")
```

**YADB 文件位置**：
- 项目根目录：`C:\Project\IDEA\gelab-zero\yadb`
- 设备路径：`/data/local/tmp/yadb`
- MD5 校验：`29a0cd3b3adea92350dd5a25594593df`

---

## 屏幕方向检测

### 为什么需要检测屏幕方向

当设备旋转时（横屏/竖屏），坐标系统会发生变化：
- 竖屏：width < height
- 横屏：width > height

如果使用固定的 `wm_size` 进行坐标转换，会导致点击位置错误。

### 屏幕方向检测实现

```python
def _detect_screen_orientation(device_id):
    """
    检测设备的屏幕方向

    Returns:
        int: 方向值
            0 - 竖屏（PORTRAIT）
            1 - 横屏（LANDSCAPE，逆时针旋转90度）
            2 - 倒置竖屏（REVERSE PORTRAIT）
            3 - 横屏（LANDSCAPE，顺时针旋转90度）
    """
    if device_id is None:
        adb_command = "adb"
    else:
        adb_command = f"adb -s {device_id}"

    # 跨平台命令
    if os.name == 'nt':  # Windows
        command = f'{adb_command} shell dumpsys input | Select-String 'orientation=\d+' | Select -First 1 | % {{ $_.Matches.Value -replace 'orientation=', '' }}'
        result = subprocess.run(
            ["powershell.exe", "-Command", command],
            capture_output=True,
            encoding="utf-8",
            shell=False,
            check=False
        )
    else:  # Unix/Linux/Mac
        command = f'''{adb_command} shell dumpsys input | grep -m 1 -o -E "orientation=[0-9]" | head -n 1 | grep -m 1 -o -E "[0-9]"'''
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

    result_str = result.stdout.strip()
    result = int(result_str.strip())

    return result
```

### 在坐标转换中应用方向检测

```python
def act_on_device(frontend_action, device_id, wm_size, print_command=False, reflush_app=True):
    if action_type == "CLICK":
        # 检测屏幕方向
        orientation = _detect_screen_orientation(device_id)

        # 如果是横屏（1或3），交换宽高
        if orientation in [1, 3]:
            wm_size = (wm_size[1], wm_size[0])

        # 转换坐标
        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)

        # 执行点击
        cmd = f"adb -s {device_id} shell input tap {x} {y}"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)
```

### 方向值说明

| 方向值 | 名称 | 说明 | 坐标变换 |
|--------|------|------|----------|
| 0 | PORTRAIT | 竖屏（正常） | 无需变换 |
| 1 | LANDSCAPE | 横屏（逆时针90°） | 交换 width 和 height |
| 2 | REVERSE_PORTRAIT | 倒置竖屏 | 交换 width 和 height |
| 3 | LANDSCAPE | 横屏（顺时针90°） | 交换 width 和 height |

---

## 应用启动机制

### Monkey 命令详解

```python
# 完整命令格式
adb shell monkey -p <package_name> -c android.intent.category.LAUNCHER 1

# 实际示例
adb shell monkey -p com.tencent.mm -c android.intent.category.LAUNCHER 1
```

**参数说明**：
- `-p <package_name>`：指定要测试的应用包名
- `-c android.intent.category.LAUNCHER`：指定启动类别（LAUNCHER 类别）
- `1`：只执行一次启动事件

### 完整的应用启动流程

```python
elif action_type == "AWAKE":
    assert "value" in frontend_action, "Missing value in AWAKE action"
    app_name = frontend_action["value"]

    # 1. 查找包名
    package_name = find_package_name(app_name)
    if package_name is None:
        raise ValueError(f"App name {app_name} not found in package map.")

    # 2. 强制停止应用（可选，用于刷新应用状态）
    if reflush_app:
        cmd = f"adb -s {device_id} shell am force-stop {package_name}"
        if print_command:
            print(f"Executing command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        time.sleep(1)  # 等待应用完全停止

    # 3. 使用 monkey 命令启动应用
    cmd = f"adb -s {device_id} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
    if print_command:
        print(f"Executing command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    return result
```

### 包名映射系统

项目维护了 200+ 应用的包名映射表（`package_map.py`）：

```python
package_name_map = {
    "微信": "com.tencent.mm",
    "支付宝": "com.eg.android.AlipayGphone",
    "抖音": "com.ss.android.ugc.aweme",
    "淘宝": "com.taobao.taobao",
    # ... 共200+应用
}
```

**智能模糊匹配**：
```python
def find_package_name(app_name):
    """
    查找应用包名，支持模糊匹配
    """
    app_name_lowered = app_name.lower()
    package_name = package_name_map.get(app_name_lowered, None)

    # 如果直接查找失败，使用模糊匹配
    if package_name is None:
        max_match = {"name": None, "score": 0}

        for key in package_name_map.keys():
            score = difflib.SequenceMatcher(None, app_name_lowered, key.lower()).ratio()
            if score > max_match["score"]:
                max_match["name"] = key
                max_match["score"] = score

        assert max_match['name'] is not None, f"Cannot find package name for app {app_name}"
        package_name = package_name_map[max_match['name']]

    return package_name
```

**使用示例**：
```python
# 精确匹配
find_package_name("微信")  # "com.tencent.mm"

# 模糊匹配
find_package_name("wechat")  # "com.tencent.mm" (通过相似度匹配)
find_package_name("wechat")  # "com.tencent.mm"
```

---

## 使用示例

### 基础用法

```python
from copilot_front_end.pu_frontend_executor import act_on_device
from copilot_front_end.mobile_action_helper import get_device_wm_size, list_devices

# 1. 列出所有连接的设备
devices = list_devices()
device_id = devices[0]  # 使用第一个设备

# 2. 获取设备屏幕尺寸
wm_size = get_device_wm_size(device_id)  # 例如：(1080, 2400)

# 3. 执行点击动作
click_action = {
    "action_type": "CLICK",
    "point": (500, 500)  # 归一化坐标
}
act_on_device(click_action, device_id, wm_size)

# 4. 输入文本
type_action = {
    "action_type": "TYPE",
    "value": "Hello World",
    "point": (500, 1800),
    "keyboard_exists": False
}
act_on_device(type_action, device_id, wm_size)

# 5. 启动应用
awake_action = {
    "action_type": "AWAKE",
    "value": "微信"
}
act_on_device(awake_action, device_id, wm_size)
```

### 高级用法 - BaseMoboleActionHelper

```python
from copilot_front_end.mobile_action_helper import BaseMoboleActionHelper

# 初始化助手
helper = BaseMoboleActionHelper(device_id="emulator-5554")

# 执行交互（自动处理截图、动作执行、等待）
action = {
    "action_type": "CLICK",
    "point": (500, 500),
    "explain": "点击登录按钮"
}

observation = helper.step_interaction(
    action=action,
    capture_duration=0.5,
    image_full_path="screenshots/screenshot1.png"
)

# observation 包含：
# {
#     "image": "/path/to/screenshot.png",
#     "user_comment": None  # 如果是 INFO 动作，这里会有用户输入
# }
```

### 批量执行动作

```python
# 定义任务步骤
task_steps = [
    {"action_type": "AWAKE", "value": "微信"},
    {"action_type": "WAIT", "seconds": 2.0},
    {"action_type": "CLICK", "point": (500, 1800)},  # 点击搜索框
    {"action_type": "TYPE", "value": "文件传输助手", "keyboard_exists": True},
    {"action_type": "WAIT", "seconds": 1.0},
    {"action_type": "CLICK", "point": (500, 400)},  # 点击搜索结果
]

# 执行任务
for step in task_steps:
    result = act_on_device(step, device_id, wm_size, print_command=True)
    print(f"执行步骤: {step['action_type']}")
```

### 处理不同格式

#### UI-Tars 格式

```python
ui_tars_action = {
    "action": "CLICK",
    "coordinate": [500, 500]
}

# 转换为前端动作
frontend_action = uiTars_to_frontend_action(ui_tars_action)
```

#### Step API 格式

```python
step_api_action = {
    "action": "Click",
    "args": {
        "normalized_point": [0.5, 0.5]
    }
}

# 转换为前端动作
frontend_action = step_api_to_frontend_action(step_api_action)
```

---

## 错误处理

### 参数验证

```python
def action_assertion(action: dict):
    """
    验证动作参数的合法性
    """
    assert type(action) == dict, "action must be a dict"
    assert "action_type" in action, "action must contain 'action_type'"

    action_type = action["action_type"]
    assert action_type in _ACTION_TYPE_ENUM, f"action_type {action_type} not in {_ACTION_TYPE_ENUM}"

    # 验证坐标参数
    if action_type in ["CLICK", "LONG_PRESS", "DOUBLE_TAP"]:
        assert "point" in action
        assert isinstance(action["point"], (list, tuple)) and len(action["point"]) == 2
        assert all(isinstance(x, int) and 0 <= x <= 1000 for x in action["point"])

    # 验证文本参数
    if action_type in ["TYPE", "AWAKE", "INFO"]:
        assert "value" in action and isinstance(action["value"], str)
```

### 异常处理示例

```python
try:
    result = act_on_device(action, device_id, wm_size)
    if result and result.returncode != 0:
        print(f"命令执行失败: {result.stderr}")
except ValueError as e:
    print(f"参数错误: {e}")
except subprocess.CalledProcessError as e:
    print(f"ADB 命令执行错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 常见错误及解决方案

| 错误类型 | 原因 | 解决方案 |
|---------|------|---------|
| `Device not found` | 设备未连接 | 检查 `adb devices` |
| `App name not found in package map` | 应用名称不存在 | 使用精确的应用名称或添加到映射表 |
| `Invalid orientation value` | 屏幕方向检测失败 | 检查设备是否正常启动 |
| `YADB not installed` | YADB 未安装到设备 | 运行 `init_device()` |
| `Point out of range` | 坐标超出范围 | 确保坐标在 [0, 1000] 范围内 |

---

## 性能优化建议

### 1. 批量操作

```python
# 不好的做法
for action in actions:
    act_on_device(action, device_id, wm_size)  # 每次都检测屏幕方向

# 好的做法
orientation = _detect_screen_orientation(device_id)
if orientation in [1, 3]:
    wm_size = (wm_size[1], wm_size[0])
for action in actions:
    act_on_device(action, device_id, wm_size)
```

### 2. 复用设备信息

```python
# 初始化时获取一次，后续复用
class DeviceController:
    def __init__(self, device_id):
        self.device_id = device_id
        self.wm_size = get_device_wm_size(device_id)
        self.orientation = _detect_screen_orientation(device_id)

    def execute(self, action):
        return act_on_device(action, self.device_id, self.wm_size)
```

### 3. 减少不必要的刷新

```python
# 默认会强制停止应用（refresh_app=True）
act_on_device(awake_action, device_id, wm_size, reflush_app=True)

# 如果应用已在后台，不需要刷新
act_on_device(awake_action, device_id, wm_size, reflush_app=False)  # 更快
```

---

## 总结

本项目的动作执行系统具有以下特点：

1. **设备无关性**：使用归一化坐标系统，支持不同分辨率的设备
2. **功能完整性**：覆盖所有常见的 Android 操作
3. **精确控制**：使用 YADB 实现精确的触摸和文本输入
4. **智能适配**：自动检测屏幕方向，调整坐标系统
5. **易于扩展**：清晰的动作定义，便于添加新类型
6. **错误处理**：完善的参数验证和错误处理机制

### 核心优势

- **支持中文输入**：通过 YADB 完美支持中文和特殊字符
- **精确时序控制**：长按、滑动等操作的时长可精确控制
- **智能匹配**：应用名称支持模糊匹配，使用友好
- **跨平台支持**：同时支持 Windows、Linux、macOS

### 文件位置总结

- **核心执行器**：`C:\Project\IDEA\gelab-zero\copilot_front_end\pu_frontend_executor.py`
- **设备管理**：`C:\Project\IDEA\gelab-zero\copilot_front_end\mobile_action_helper.py`
- **包名映射**：`C:\Project\IDEA\gelab-zero\copilot_front_end\package_map.py`
- **动作定义**：`C:\Project\IDEA\gelab-zero\copilot_tools\action_tools.py`
- **YADB 工具**：`C:\Project\IDEA\gelab-zero\yadb`

---

## 附录

### A. 完整的 KeyEvent 对照表

| 代码 | 按键名称 | 说明 |
|-----|---------|------|
| 3 | HOME | 主页键 |
| 4 | BACK | 返回键 |
| 24 | VOLUME_UP | 音量加 |
| 25 | VOLUME_DOWN | 音量减 |
| 26 | POWER | 电源键 |
| 27 | CAMERA | 相机键 |
| 82 | MENU | 菜单键 |
| 84 | SEARCH | 搜索键 |

### B. 屏幕方向对照表

| 方向值 | 名称 | 旋转角度 | 坐标变换 |
|--------|------|---------|----------|
| 0 | PORTRAIT | 0° | 无需变换 |
| 1 | LANDSCAPE | 90°（逆时针） | 交换 width 和 height |
| 2 | REVERSE_PORTRAIT | 180° | 交换 width 和 height |
| 3 | LANDSCAPE | 270°（顺时针） | 交换 width 和 height |

### C. 支持的应用列表（部分）

项目支持 200+ 应用，包括：
- 社交：微信、QQ、微博、抖音、小红书
- 购物：淘宝、京东、拼多多、美团
- 工具：支付宝、百度网盘、WPS Office
- 娱乐：爱奇艺、腾讯视频、网易云音乐
- 生活：高德地图、滴滴出行、携程旅行

完整列表见：`C:\Project\IDEA\gelab-zero\copilot_front_end\package_map.py`
