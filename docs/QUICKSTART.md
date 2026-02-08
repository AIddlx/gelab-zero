# 快速开始

5 分钟快速上手 gelab-zero (AIddlx 修改版)。

---

## 前置要求

- Python 3.12+
- Android 设备（已开启 USB 调试）
- ADB 工具已安装
- Ollama（本地 LLM 推理）

---

## 步骤 1: 安装依赖

```bash
pip install -r requirements.txt
```

---

## 步骤 2: 下载模型

```bash
# 下载 GELab-Zero-4B-preview
hf download stepfun-ai/GELab-Zero-4B-preview --local-dir gelab-zero-4b-preview

# 导入 Ollama
cd gelab-zero-4b-preview
ollama create gelab-zero-4b-preview -f Modelfile
```

---

## 步骤 3: 连接设备

### 方式 1: USB 连接

用数据线连接手机和电脑，运行：

```bash
adb devices
```

应看到设备列表。

### 方式 2: 无线连接（自动）

**本版本改进**：运行脚本后会自动启用无线模式，无需手动配置！

```bash
# 插上 USB 线运行一次，之后可拔线
python examples/run_single_task.py "测试"
```

脚本会自动：
1. 检测 USB 设备
2. 启用无线 ADB (`adb tcpip 5555`)
3. 获取设备 IP
4. 建立无线连接

拔线后，下次运行会自动扫描局域网连接设备。

---

## 步骤 4: 运行任务

### 单任务模式

```bash
python examples/run_single_task.py "打开计算器"
```

### 交互式对话模式（新增）

```bash
python examples/run_interactive.py
```

支持命令：
- `/quit` - 退出
- `/clear` - 清屏
- `/devices` - 列出设备

---

## 输出说明

执行过程中会显示实时进度：

```
▶ Step 1/400 (10.0s) - CLICK (448,19)
    说明: 点击搜索栏
    摘要: 激活搜索功能
  📸 截图: running_log/.../session_id_step_1.jpeg
```

日志位置：
- 文本日志：`running_log/logs/run_single_task_*.log`
- 轨迹日志：`running_log/server_log/os-copilot-local-eval-logs/traces/*.jsonl`
- 截图保存：`running_log/server_log/os-copilot-local-eval-logs/images/`

---

## 可视化轨迹

```bash
streamlit run visualization/main_page.py --server.port 33503
```

浏览器打开 `http://localhost:33503`

---

## 常见问题

### Q: 没有检测到设备？

**A:** 检查：
1. 手机是否开启 USB 调试
2. 是否已授权电脑调试
3. 运行 `adb devices` 确认

### Q: 视频窗口白屏？

**A:** 参考 [TROUBLESHOOTING](docs/TROUBLESHOOTING_VIDEO_FREEZE.md)

### Q: 中文输入乱码？

**A:** 本版本使用 scrcpy，原生支持中文，不会乱码。

---

## 下一步

- [scrcpy 集成说明](SCRCPY_INTEGRATION.md) - 了解设备控制改进
- [MCP 服务器](docs/MCP_SERVER.md) - 多设备管理
