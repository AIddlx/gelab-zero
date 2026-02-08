# 阶跃桌面助手 - 添加 GELab 单步动作 MCP 工具指南

本文档介绍如何在阶跃桌面助手中添加 GELab 单步动作 MCP 工具。

## 前置要求

- 已安装阶跃桌面助手
- 已完成 [GELab-Zero 安装步骤](SETUP_GUIDE.md)
- Ollama 模型服务已启动

## 准备工作

### 1. 启动 Ollama 模型服务

```bash
ollama run gelab-zero-4b-preview
```

**保持此窗口运行**，不要关闭。

### 2. 启动 GELab 单步动作 MCP 服务器

```bash
cd gelab-zero
python mcp_server/single_action_mcp_server.py
```

服务器默认运行在 `http://127.0.0.1:8705/mcp`

**保持此窗口运行**，不要关闭。

---

## 添加步骤

### 步骤 1: 显示主窗口

在电脑右下角找到"小跃"图标，**右键点击** → 选择"显示主窗口"

### 步骤 2: 进入设置页面

在主窗口**右上角**，**左键点击**圆形图标 → 进入设置页面

### 步骤 3: 找到工具箱

在设置页面中，找到并点击"**工具箱**"选项

### 步骤 4: 添加外部工具

在工具箱页面，点击"**添加外部工具**"

### 步骤 5: 配置 MCP 工具

选择"**添加外部 MCP 工具**"，填写以下信息：

| 参数 | 值 | 说明 |
|------|---|------|
| 名称 | `gelab-single-action` | 自定义名称，用于识别工具 |
| URL | `http://127.0.0.1:8705/mcp` | MCP 服务器地址 |

填写完成后，点击"**确认**"或"**添加**"按钮。

---

## 可用功能

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| list_devices | 列出已连接设备 | 显示设备列表 |
| screenshot | 获取设备截图 | 保存截图文件 |
| do_action | 执行单步动作 | "点击搜索框"、"输入Hello" |

**do_action 支持的动作：**
- 点击：`"点击搜索框"`
- 输入：`"输入Hello"`
- 滑动：`"向上滑动"`
- 按键：`"按返回键"`
- Home：`"返回主页"`
- 等待：`"等待2秒"`

---

## 使用示例

### 示例 1: 打开应用并搜索

```
用户: 打开哔哩哔哩，搜索"猫咪视频"

阶跃桌面助手会循环调用：
1. do_action("点击应用抽屉")
2. do_action("搜索哔哩哔哩")
3. do_action("点击哔哩哔哩图标")
4. do_action("点击搜索框")
5. do_action("输入猫咪视频")
6. do_action("按搜索键")
```

### 示例 2: 发送微信消息

```
用户: 给张三发送消息"晚上一起吃饭？"

阶跃桌面助手会循环调用：
1. do_action("点击微信图标")
2. do_action("点击搜索")
3. do_action("输入张三")
4. do_action("点击张三头像")
5. do_action("点击输入框")
6. do_action("输入晚上一起吃饭？")
7. do_action("按发送键")
```

---

## 返回结果说明

每次调用 `do_action` 返回：

```json
{
  "thinking": "我看到搜索框在顶部中央",
  "predicted_action": {"action": "click", "coordinate": [540, 120]},
  "executed": true,
  "execution_result": "已点击 (540, 120)",
  "screenshot_after_path": "C:/.../after_20250208_123456.png"
}
```

阶跃桌面助手会：
1. 查看 `thinking` 了解模型思考
2. 查看 `screenshot_after_path` 获取执行后的截图
3. 根据截图决定下一步指令

---

## 配置文件示例

```json
{
  "mcpServers": {
    "gelab-single-action": {
      "url": "http://127.0.0.1:8705/mcp"
    }
  }
}
```

---

## 常见问题

### 1. 连接失败

- 确保 single_action_mcp_server.py 已启动
- 检查端口号 8705 是否被占用
- 确认 Ollama 模型服务已启动

### 2. 动作执行失败

- 确保设备已连接（USB 或无线）
- 检查设备屏幕是否亮起
- 查看日志文件：`running_log/mcp_server/single_action_mcp_*.log`

### 3. 模型响应慢

- 确认 Ollama 服务正常运行
- 检查模型是否已下载：`ollama list`
- 首次调用可能较慢（模型加载）

---

## 与详细 MCP 的区别

GELab 提供两种 MCP 服务器：

| 特性 | 单步动作 MCP | 详细 MCP |
|------|-------------|----------|
| 文件 | `single_action_mcp_server.py` | `detailed_gelab_mcp_server.py` |
| 端口 | 8705 | 8704 |
| 用途 | 单步控制，适合阶跃桌面助手 | 完整任务，适合 Claude Code |
| 工具 | do_action（单步） | ask_agent（完整任务） |
| 上层 AI | 阶跃桌面助手 | Claude Code |

**推荐配置：**
- 阶跃桌面助手 → 单步动作 MCP（8705）
- Claude Code → 详细 MCP（8704）
