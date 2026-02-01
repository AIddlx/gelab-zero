# scrcpy 集成说明

本版本使用 [scrcpy-py-ddlx](https://github.com/AIddlx/scrcpy_py_ddlx) 替代 ADB 进行设备控制。

---

## 为什么使用 scrcpy？

| 特性 | ADB | scrcpy-py-ddlx |
|------|-----|----------------|
| 速度 | 慢 | **快 5-10 倍** |
| 截图延迟 | ~500ms | ~20ms (**25x**) |
| 中文输入 | 不支持 | **原生支持** |
| 视频流 | 无 | **实时预览** |
| 音频支持 | 无 | **有** |
| 无线连接 | 需手动配置 | **自动切换** |

---

## 架构

### 双执行路径

```
┌─────────────────────────────────────────────────┐
│             gelab-zero 主控制逻辑                  │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────┐      ┌───────────────┐
│   scrcpy      │      │     ADB       │
│  (主路径)      │      │   (备用)       │
└───────────────┘      └───────────────┘
```

**主路径**：`ScrcpyDeviceController` - 快速、稳定
**备用路径**：`PuFrontendExecutor` - ADB 回退方案

---

## 使用方式

### 基础控制

```python
from copilot_front_end.scrcpy_device_controller import ScrcpyDeviceController

controller = ScrcpyDeviceController(device_id)

# 基础操作
controller.tap(500, 300)              # 点击
controller.swipe(x1, y1, x2, y2)      # 滑动
controller.inject_text("你好")        # 输入中文
controller.home()                     # 返回主页
controller.back()                     # 返回键
controller.screenshot()                # 截图
```

### 连接管理

```python
from copilot_front_end.scrcpy_connection_manager import get_scrcpy_manager

manager = get_scrcpy_manager()

# 获取客户端（自动连接）
client = manager.get_client(device_id, show_window=True)

# 截图（超快速，内存模式）
screenshot_array = client.screenshot()  # 返回 numpy 数组

# 断开连接
manager.disconnect(device_id)
```

### 自动设备发现

**本版本新增功能**：

```python
# 1. USB 设备自动启用无线
# 检测到 USB 连接后，自动执行：
#   adb tcpip 5555
#   adb connect <IP>:5555

# 2. 局域网扫描
# 自动扫描网段内的 ADB 设备并连接

# 代码位置：examples/run_single_task.py 第 323-542 行
```

---

## 支持的动作

| 动作 | 方法 | 说明 |
|------|------|------|
| CLICK | `tap(x, y)` | 点击屏幕 |
| TYPE | `inject_text(text)` | 输入文本（支持中文） |
| SWIPE | `swipe(x1, y1, x2, y2)` | 滑动 |
| LONGPRESS | `long_press(x, y)` | 长按 |
| SCROLL | `scroll(direction)` | 滚动 |
| HOME | `home()` | 返回主页 |
| BACK | `back()` | 返回键 |
| ENTER | `enter()` | 回车键 |
| SCREENSHOT | `screenshot()` | 截图 |

---

## 性能对比

### 操作延迟

| 操作 | ADB | scrcpy | 提升 |
|------|-----|--------|------|
| 点击 | ~200ms | ~30ms | **6.7x** |
| 滑动 | ~300ms | ~50ms | **6x** |
| 输入文本 | ~400ms | ~50ms | **8x** |
| 截图 | ~500ms | ~20ms | **25x** |

---

## 双链路模式（USB + 无线）

**本版本新增**：自动切换，无缝衔接

1. **初始连接**：USB 数据线连接
2. **自动启用无线**：`adb tcpip 5555` + 获取 IP
3. **拔线继续**：自动切换到无线连接
4. **下次运行**：自动扫描并连接无线设备

---

## 实时预览窗口

```python
# 显示设备屏幕（实时视频流）
client = manager.get_client(device_id, show_window=True)

# 窗口显示：
# - 设备屏幕（H.264 视频流）
# - 每步操作耗时
# - 截图保存位置
```

---

## 故障排除

### 无法连接设备

```bash
# 检查 ADB
adb devices

# 手动启用无线
adb tcpip 5555
adb connect <设备IP>:5555
```

### 视频窗口白屏

参考 [TROUBLESHOOTING](docs/TROUBLESHOOTING_VIDEO_FREEZE.md)

### 中文输入问题

scrcpy 原生支持 UTF-8，不会乱码。如果出现乱码：
1. 检查终端编码
2. 确认 Python 源码为 UTF-8

---

## 相关项目

- [scrcpy-py-ddlx](https://github.com/AIddlx/scrcpy_py_ddlx) - Python scrcpy 客户端
- [官方 scrcpy](https://github.com/Genymobile/scrcpy) - 原项目
- [yadb](https://github.com/ysbing/yadb) - ADB 增强，支持网络 ADB
