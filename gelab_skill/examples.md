# GELab-Zero 使用示例

本文档提供了 GELab-Zero 的常见使用示例，供 AI Agent 参考。

## 基础操作示例

### 示例 1: 打开应用

```bash
# 打开计算器
python examples/run_single_task.py "打开计算器"

# 打开设置
python examples/run_single_task.py "打开系统设置"

# 打开微信
python examples/run_single_task.py "打开微信应用"
```

### 示例 2: 导航操作

```bash
# 返回桌面
python examples/run_single_task.py "按返回键回到桌面"

# 返回上一页
python examples/run_single_task.py "点击返回按钮"

# 下滑通知栏
python examples/run_single_task.py "从顶部向下滑动，打开通知栏"
```

### 示例 3: 文本输入

```bash
# 搜索内容
python examples/run_single_task.py "打开浏览器，在搜索框输入 Python 教程"

# 发送消息
python examples/run_single_task.py "打开微信，找到文件传输助手，发送消息你好"
```

## 复杂任务示例

### 示例 4: 购物流程

```bash
# 完整购物流程
python examples/run_single_task.py "打开淘宝，搜索 iPhone 15，按销量排序，查看第一个商品"
```

执行步骤（自动生成）：
1. 打开淘宝应用
2. 点击搜索框
3. 输入 "iPhone 15"
4. 点击搜索按钮
5. 点击排序筛选
6. 选择按销量排序
7. 点击第一个商品

### 示例 5: 信息查询

```bash
# 查询天气
python examples/run_single_task.py "打开天气应用，查看今天的天气"

# 查询地铁线路
python examples/run_single_task.py "打开高德地图，搜索从当前地点到火车站的路线"
```

### 示例 6: 系统设置

```bash
# 修改设置
python examples/run_single_task.py "进入设置，关闭自动亮度调节"

# 连接 WiFi
python examples/run_single_task.py "进入设置，打开 WiFi，连接到 HomeNetwork"
```

## 应用特定示例

### 微信操作

```bash
# 发送消息
python examples/run_single_task.py "打开微信，找到张三，发送消息今天晚上一起吃饭"

# 朋友圈
python examples/run_single_task.py "打开微信朋友圈，滑动查看动态"

# 扫码支付
python examples/run_single_task.py "打开微信扫一扫"
```

### 淘宝操作

```bash
# 搜索商品
python examples/run_single_task.py "打开淘宝，搜索机械键盘"

# 查看购物车
python examples/run_single_task.py "打开淘宝，进入购物车"

# 查看订单
python examples/run_single_task.py "打开淘宝，进入我的订单"
```

### 抖音操作

```bash
# 刷视频
python examples/run_single_task.py "打开抖音，向上滑动刷视频"

# 点赞视频
python examples/run_single_task.py "打开抖音，双击屏幕点赞"

# 搜索用户
python examples/run_single_task.py "打开抖音，搜索某个用户"
```

## 多步骤任务示例

### 示例 7: 网上购物完整流程

```bash
# 步骤 1: 搜索商品
python examples/run_single_task.py "打开淘宝，搜索 Python 编程入门书籍"

# 步骤 2: 筛选排序
python examples/run_single_task.py "点击筛选，选择销量从高到低排序"

# 步骤 3: 查看详情
python examples/run_single_task.py "点击第一个商品，查看商品详情和评价"

# 步骤 4: 加入购物车
python examples/run_single_task.py "点击加入购物车"
```

### 示例 8: 社交媒体互动

```bash
# 发布朋友圈
python examples/run_single_task.py "打开微信朋友圈，点击发布，输入今天天气真好"

# 评论互动
python examples/run_single_task.py "打开朋友圈，找到第一条动态，点赞并评论"
```

## 常见场景示例

### 场景 1: 查询信息

```bash
# 查询股票
python examples/run_single_task.py "打开支付宝，搜索股票查询，查看苹果公司股价"

# 查询外卖
python examples/run_single_task.py "打开饿了么，搜索附近的奶茶店"

# 查询新闻
python examples/run_single_task.py "打开今日头条，浏览今日热点新闻"
```

### 场景 2: 生活服务

```bash
# 点外卖
python examples/run_single_task.py "打开美团外卖，选择附近的肯德基，点一个香辣鸡腿堡套餐"

# 打车
python examples/run_single_task.py "打开滴滴出行，输入目的地北京南站，叫车"

# 充值缴费
python examples/run_single_task.py "打开支付宝，充值话费 50 元"
```

### 场景 3: 娱乐休闲

```bash
# 看视频
python examples/run_single_task.py "打开抖音，搜索萌宠视频"

# 听音乐
python examples/run_single_task.py "打开网易云音乐，播放周杰伦的歌曲"

# 玩游戏
python examples/run_single_task.py "打开王者荣耀，开始匹配游戏"
```

## 高级示例

### 示例 9: 需要用户交互的任务

```bash
# INFO 动作会暂停等待用户输入
python examples/run_single_task.py "打开浏览器，访问百度，询问我要搜索什么"
```

当任务执行到需要用户输入时，会在控制台提示：
```
INFO: 需要用户输入...
请输入: [用户输入的内容]
```

### 示例 10: 长时间运行的任务

```bash
# 下载文件
python examples/run_single_task.py "打开浏览器，下载一个大文件，等待下载完成"

# 观看视频
python examples/run_single_task.py "打开抖音，连续观看 10 个视频"
```

## 任务描述技巧

### 具体化

✅ **具体**：
- "点击屏幕中央的计算器图标"
- "在搜索框输入 Python 教程"

❌ **模糊**：
- "点击按钮"（哪个按钮？）
- "输入内容"（输入什么？）

### 顺序化

✅ **有序**：
- "先打开微信，再找到张三，最后发送消息"

❌ **无序**：
- "在微信里给张三发消息"

### 完整性

✅ **完整**：
- "打开淘宝，搜索 iPhone，按价格从低到高排序，查看前 3 个商品"

❌ **不完整**：
- "淘宝看手机"

## 输出解读

### 成功执行

```
Step 1/400 (2.3s) - CLICK (500.00, 300.00) "计算器"
  📸 截图: running_log/.../session_123_step_1.jpeg

Step 2/400 (1.8s) - TYPE "123"
  📸 截图: running_log/.../session_123_step_2.jpeg

Step 3/400 (0.5s) - COMPLETE "任务完成"
  说明: 计算器已打开并输入数字

✅ 任务完成！
```

### 失败执行

```
Step 5/400 (3.2s) - INFO "请确认是否继续"

❌ 任务执行失败：未收到用户输入
```

## 调试技巧

### 查看详细日志

```bash
# 日志文件位置
running_log/logs/run_single_task_YYYYMMDD_HHMMSS.log

# 查看实时日志
tail -f running_log/logs/run_single_task_*.log
```

### 查看执行轨迹

```bash
# JSONL 轨迹文件
running_log/server_log/os-copilot-local-eval-logs/traces/*.jsonl

# 使用 jq 解析
cat traces/*.jsonl | jq '.action'
```

### 查看截图

```bash
# 截图目录
running_log/server_log/os-copilot-local-eval-logs/images/

# 使用图片查看器
python -m http.server 8000
# 然后访问 http://localhost:8000/running_log/...
```
