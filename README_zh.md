[English](README.md) | [中文](README_zh.md)

# ADB Agent

一个 [OpenClaw](https://github.com/openclaw/openclaw) Skill，让 AI 智能体通过 ADB + [uiautomator2](https://github.com/openatx/uiautomator2) 控制任意 Android 手机。AI 读取 UI 树，自主决定点击/输入/滑动操作，并验证结果——全部通过一个 CLI 工具完成。

## 功能特性

- **完整手机控制** — 点击、输入（支持中文）、滑动、滚动、锁屏/解锁、截图
- **AI 优化输出** — UI 树以紧凑 JSON 输出；滚动提示以 `[重要提示]` 显示在 JSON 之前
- **节省 Token** — 多种 dump 模式（interactive、numbered、search、diff）最小化上下文消耗
- **安全内置** — 支付页面检测、敏感关键词拦截、操作审计日志
- **自愈能力** — 自动重连、agent 重启、弹窗自动处理
- **批量执行** — `batch-steps` 一次调用执行多个操作，减少通信轮次

## 工作原理

```
AI Agent ──→ ./phone ui dump --interactive --numbered
         ←── [重要提示] 纵向可滚动(ViewPager)...
              {"package":"com.tencent.mm","elements":[{"index":1,"class":"TextView","text":"微信",...}]}

AI Agent ──→ ./phone input tap-nth 3
         ←── {"status":"ok","data":["Tapped #3 at (360,400)"]}
```

1. AI 调用 `ui dump` 获取屏幕结构化 JSON
2. AI 按元素编号调用 `tap-nth`、`tap-text` 或 `input text`
3. AI 重新 dump 验证操作结果
4. 所有命令默认输出 JSON（用 `--plain` 切换纯文本）

## 环境要求

### 主机（macOS / Linux）

```bash
brew install android-platform-tools   # 或: apt install adb
pip install uiautomator2 lxml Pillow PyYAML
```

### Android 手机

1. 开启 **开发者选项**（设置 → 关于手机 → 连续点击版本号 7 次）
2. 开启 **USB 调试**
3. ColorOS/MIUI 还需开启 **USB 调试（安全设置）**
4. 首次通过 USB 连接初始化：
   ```bash
   adb devices                    # 确认连接
   python -m uiautomator2 init    # 在手机上安装 ATX agent
   ```

## 快速开始

```bash
# 初始化配置
cp config.yaml.example config.yaml

# 检查连接
./phone status

# 查看屏幕（AI 最常用的命令）
./phone ui dump --interactive --numbered

# 按编号点击
./phone input tap-nth 3

# 按文本点击
./phone input tap-text "搜索"

# 输入文字（支持中文）
./phone input text "Hello 你好"

# 启动应用
./phone app launch com.tencent.mm

# 截图
./phone screenshot
```

## JSON 输出

所有命令默认输出 JSON，有两种格式：

**UI Dump**（自定义格式，滚动提示在前）：
```
[重要提示] 纵向可滚动(ViewPager)，当前仅显示可见部分。如需查看更多: 'input swipe 360 1069 360 356'。
{"package":"com.tencent.mm","activity":".ui.LauncherUI","screen":{"width":720,"height":1604},"elements":[...]}
```

**其他命令**（标准包装格式）：
```json
{"status":"ok","command":"input tap-text","timestamp":"2026-03-04T02:35:00","duration_ms":1250,"data":["Tapped \"搜索\" at (540,200)"]}
```

## WiFi ADB（可选）

```bash
adb tcpip 5555
adb connect <手机IP>:5555
# 然后编辑 config.yaml: device: "<手机IP>:5555", mode: "wifi"
```

## 项目结构

```
adb-agent/
├── SKILL.md                 # AI 操作手册（由 OpenClaw 加载）
├── phone                    # 包装脚本（自动激活 venv）
├── config.yaml.example      # 配置模板
├── requirements.txt         # Python 依赖
├── scripts/
│   └── phone_control.py     # CLI 入口
├── tools/phone/             # 核心模块
│   ├── ui.py                # UI 树 dump / find / diff
│   ├── input_ctrl.py        # 点击 / 滑动 / 输入 / 按键
│   ├── app.py               # 应用管理
│   ├── device.py            # 屏幕 / 锁屏 / 音量 / WiFi
│   ├── automation.py        # 等待 / 断言 / 批量 / 宏
│   ├── safety.py            # 支付拦截 / 审计
│   └── ...                  # contacts, media, file_mgr 等
└── references/              # 详细文档（AI 按需加载）
```

## 安全机制

- 自动拦截支付页面（支付宝、微信支付、银行类应用）
- 危险操作需要 `--confirm` 确认
- 所有操作记录审计日志
- 可配置敏感关键词和包名

## 配置

复制 `config.yaml.example` 为 `config.yaml` 并按需修改：
- 设备连接方式（USB / WiFi）
- 超时设置
- 敏感包名和关键词
- 屏幕尺寸

## 许可证

MIT
