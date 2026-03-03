[English](README.md) | [中文](README_zh.md)

# ADB Agent

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/yourusername/adb-agent/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#installation)

An [OpenClaw](https://github.com/openclaw/openclaw) Skill that lets AI agents control any Android phone via ADB + [uiautomator2](https://github.com/openatx/uiautomator2). The AI reads the UI tree, decides what to tap/type/swipe, and verifies the result — all through a single CLI tool.

## Features

- **Full phone control** — tap, type (CJK supported), swipe, scroll, lock/unlock, screenshot
- **AI-optimized output** — numbered UI dump as compact JSON with scroll hints
- **Token efficient** — multiple dump modes (interactive, numbered, search, diff) to minimize context usage
- **Safety built-in** — payment screen detection, sensitive keyword blocking, operation audit log
- **Self-healing** — auto-reconnect, agent restart, popup auto-dismiss via watchers
- **Batch execution** — `batch-steps` runs multiple actions in one call to save round-trips
- **Cross-platform** — works on macOS, Linux, and Windows

## How It Works

```
AI Agent ──→ ./phone ui dump --interactive --numbered
         ←── {"package":"com.xingin.xhs","elements":[{"index":1,"class":"TextView","text":"Explore",...}]}

AI Agent ──→ ./phone input tap-nth 3
         ←── {"status":"ok","data":["Tapped #3 at (360,400)"]}
```

1. AI calls `ui dump` to see the screen as structured JSON
2. AI picks an element by index and calls `tap-nth`, `tap-text`, or `input text`
3. AI re-dumps to verify the result
4. All commands output JSON by default (use `--plain` for plain text)

## Installation

### Step 1: Install Python 3.8+

**macOS:**
```bash
brew install python3
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install python3 python3-pip python3-venv
```

**Windows:**

Download and install from [python.org](https://www.python.org/downloads/). During installation, check **"Add Python to PATH"**.

### Step 2: Install ADB (Android Debug Bridge)

**macOS:**
```bash
brew install android-platform-tools
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install android-tools-adb
```

**Windows:**

Download [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) from Google, extract the zip, and add the folder to your system `PATH`.

### Step 3: Install Python Dependencies

```bash
cd adb-agent
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Step 4: Prepare Your Android Phone

1. **Enable Developer Options**: Go to Settings → About Phone → tap **Build Number** 7 times
2. **Enable USB Debugging**: Settings → Developer Options → toggle **USB Debugging** on
3. **For ColorOS (OPPO/Realme/OnePlus)**: Also enable **USB Debugging (Security Settings)** — required for UI automation
4. **For MIUI (Xiaomi/Redmi/POCO)**: Also enable **USB Debugging (Security Settings)** and **Install via USB**
5. **Connect via USB** and approve the "Allow USB Debugging" prompt on the phone
6. **Verify connection**:
   ```bash
   adb devices
   # Should show your device as "device" (not "unauthorized")
   ```
7. **Install ATX Agent** on the phone (first time only):
   ```bash
   python -m uiautomator2 init
   ```
   This installs a small helper app on the phone that enables UI automation.

### Step 5: Configure

```bash
cp config.yaml.example config.yaml
# Edit config.yaml to match your device (screen size, connection mode, etc.)
```

## Quick Start

```bash
# Check connection
./phone status

# View screen (AI's primary command)
./phone ui dump --interactive --numbered

# Tap by index from dump
./phone input tap-nth 3

# Tap by visible text
./phone input tap-text "Search"

# Type text (CJK supported)
./phone input text "Hello World"

# Launch app (e.g. RedNote / Xiaohongshu)
./phone app launch com.xingin.xhs

# Screenshot
./phone screenshot
```

> **Windows note:** Use `python scripts/phone_control.py` instead of `./phone`, since the shell wrapper is for Unix systems.

## JSON Output

All commands output JSON by default. Two formats:

**UI Dump** (custom format, scroll hints printed before JSON):
```
[Hint] Vertically scrollable (ViewPager). Swipe to see more: 'input swipe 360 1069 360 356'.
{"package":"com.xingin.xhs","activity":".index.v2.IndexActivityV2","screen":{"width":720,"height":1604},"elements":[...]}
```

**All other commands** (standard wrapper):
```json
{"status":"ok","command":"input tap-text","timestamp":"2026-03-04T02:35:00","duration_ms":1250,"data":["Tapped \"Search\" at (540,200)"]}
```

## WiFi ADB (Optional)

Once initial USB setup is complete, you can switch to wireless:

```bash
# With phone connected via USB:
adb tcpip 5555
adb connect <phone-ip>:5555

# Then edit config.yaml:
# device: "<phone-ip>:5555"
# mode: "wifi"
# wifi_ip: "<phone-ip>"
```

## Project Structure

```
adb-agent/
├── SKILL.md                 # AI operation manual (loaded by OpenClaw)
├── phone                    # Wrapper script (auto-activates venv, macOS/Linux)
├── config.yaml.example      # Configuration template
├── requirements.txt         # Python dependencies
├── scripts/
│   └── phone_control.py     # CLI entry point
├── tools/phone/             # Core modules
│   ├── ui.py                # UI tree dump / find / diff
│   ├── input_ctrl.py        # Tap / swipe / text / key / gesture
│   ├── app.py               # App management
│   ├── device.py            # Screen / lock / volume / wifi
│   ├── automation.py        # Wait / assert / batch / macro
│   ├── safety.py            # Payment blocking / audit
│   └── ...                  # contacts, media, file_mgr, etc.
└── references/              # Detailed docs (loaded by AI on demand)
```

## Safety

- Payment screens auto-blocked (Alipay, WeChat Pay, banking apps)
- Dangerous commands require `--confirm` flag
- All operations logged to audit file
- Configurable sensitive keywords and packages

## Configuration

Copy `config.yaml.example` to `config.yaml` and customize:
- **Device connection** — USB or WiFi mode, device serial or IP
- **Timeouts** — per-operation timeout values (UI dump, app launch, etc.)
- **Sensitive packages** — apps where automation is blocked (payment, banking)
- **Sensitive keywords** — text patterns that trigger operation pause
- **Screen dimensions** — width and height of your device screen

## Supported Devices

Tested on various Android devices including:
- OPPO / Realme / OnePlus (ColorOS)
- Xiaomi / Redmi / POCO (MIUI / HyperOS)
- Samsung (One UI)
- Stock Android (Pixel, etc.)

Requires Android 7.0+ with USB Debugging enabled.

## License

MIT
