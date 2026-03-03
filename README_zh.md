[English](README.md) | [中文](README_zh.md)

# ADB Agent

[![版本](https://img.shields.io/badge/版本-1.0.0-blue.svg)](https://github.com/yourusername/adb-agent/releases)
[![许可证](https://img.shields.io/badge/许可证-MIT-green.svg)](LICENSE)
[![平台](https://img.shields.io/badge/平台-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#安装步骤)

一个 [OpenClaw](https://github.com/openclaw/openclaw) Skill，让 AI 智能体通过 ADB + [uiautomator2](https://github.com/openatx/uiautomator2) 控制任意 Android 手机。AI 读取 UI 树，自主决定点击/输入/滑动操作，并验证结果——全部通过一个 CLI 工具完成。

## 功能特性

- **完整手机控制** — 点击、输入（支持中文）、滑动、滚动、锁屏/解锁、截图
- **AI 优化输出** — UI 树以紧凑 JSON 输出，附带滚动提示
- **节省 Token** — 多种 dump 模式（interactive、numbered、search、diff）最小化上下文消耗
- **安全内置** — 支付页面检测、敏感关键词拦截、操作审计日志
- **自愈能力** — 自动重连、agent 重启、弹窗自动处理
- **批量执行** — `batch-steps` 一次调用执行多个操作，减少通信轮次
- **跨平台** — 支持 macOS、Linux 和 Windows

## 工作原理

```
AI Agent ──→ ./phone ui dump --interactive --numbered
         ←── {"package":"com.xingin.xhs","elements":[{"index":1,"class":"TextView","text":"探索",...}]}

AI Agent ──→ ./phone input tap-nth 3
         ←── {"status":"ok","data":["Tapped #3 at (360,400)"]}
```

1. AI 调用 `ui dump` 获取屏幕结构化 JSON
2. AI 按元素编号调用 `tap-nth`、`tap-text` 或 `input text`
3. AI 重新 dump 验证操作结果
4. 所有命令默认输出 JSON（用 `--plain` 切换纯文本）

## 安装步骤

### 第 1 步：安装 Python 3.8+

**macOS：**
```bash
brew install python3
```

**Linux (Debian/Ubuntu)：**
```bash
sudo apt install python3 python3-pip python3-venv
```

**Windows：**

从 [python.org](https://www.python.org/downloads/) 下载安装。安装时勾选 **"Add Python to PATH"**。

### 第 2 步：安装 ADB（Android 调试桥）

**macOS：**
```bash
brew install android-platform-tools
```

**Linux (Debian/Ubuntu)：**
```bash
sudo apt install android-tools-adb
```

**Windows：**

从 Google 下载 [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools)，解压后将文件夹添加到系统 `PATH`。

### 第 3 步：安装 Python 依赖

```bash
cd adb-agent
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 第 4 步：准备 Android 手机

1. **开启开发者选项**：设置 → 关于手机 → 连续点击**版本号** 7 次
2. **开启 USB 调试**：设置 → 开发者选项 → 打开 **USB 调试**
3. **ColorOS（OPPO/Realme/一加）**：还需开启 **USB 调试（安全设置）** — UI 自动化必需
4. **MIUI（小米/Redmi/POCO）**：还需开启 **USB 调试（安全设置）** 和 **通过 USB 安装应用**
5. **通过 USB 连接**，在手机上点击"允许 USB 调试"
6. **验证连接**：
   ```bash
   adb devices
   # 应显示你的设备状态为 "device"（不是 "unauthorized"）
   ```
7. **安装 ATX Agent**（仅首次需要）：
   ```bash
   python -m uiautomator2 init
   ```
   这会在手机上安装一个小工具应用，用于启用 UI 自动化。

### 第 5 步：配置

```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml，根据你的设备调整（屏幕尺寸、连接方式等）
```

## 快速开始

```bash
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

# 启动应用（以小红书为例）
./phone app launch com.xingin.xhs

# 截图
./phone screenshot
```

> **Windows 用户注意：** 使用 `python scripts/phone_control.py` 代替 `./phone`，因为 shell 包装脚本仅适用于 Unix 系统。

## JSON 输出

所有命令默认输出 JSON，有两种格式：

**UI Dump**（自定义格式，滚动提示在 JSON 之前输出）：
```
[重要提示] 纵向可滚动(ViewPager)，当前仅显示可见部分。如需查看更多: 'input swipe 360 1069 360 356'。
{"package":"com.xingin.xhs","activity":".index.v2.IndexActivityV2","screen":{"width":720,"height":1604},"elements":[...]}
```

**其他命令**（标准包装格式）：
```json
{"status":"ok","command":"input tap-text","timestamp":"2026-03-04T02:35:00","duration_ms":1250,"data":["Tapped \"搜索\" at (540,200)"]}
```

## WiFi ADB（可选）

USB 初始设置完成后，可以切换到无线连接：

```bash
# 手机通过 USB 连接时：
adb tcpip 5555
adb connect <手机IP>:5555

# 然后编辑 config.yaml：
# device: "<手机IP>:5555"
# mode: "wifi"
# wifi_ip: "<手机IP>"
```

## 项目结构

```
adb-agent/
├── SKILL.md                 # AI 操作手册（由 OpenClaw 加载）
├── phone                    # 包装脚本（自动激活 venv，macOS/Linux）
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
- **设备连接** — USB 或 WiFi 模式，设备序列号或 IP
- **超时设置** — 各操作的超时时间（UI dump、应用启动等）
- **敏感包名** — 禁止自动化操作的应用（支付、银行类）
- **敏感关键词** — 触发操作暂停的文本模式
- **屏幕尺寸** — 设备屏幕的宽度和高度

## 支持的设备

已在以下 Android 设备上测试：
- OPPO / Realme / 一加（ColorOS）
- 小米 / Redmi / POCO（MIUI / HyperOS）
- 三星（One UI）
- 原生 Android（Pixel 等）

需要 Android 7.0 以上，开启 USB 调试。

## 许可证

MIT
