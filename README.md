[English](README.md) | [中文](README_zh.md)

# ADB Agent

An [OpenClaw](https://github.com/openclaw/openclaw) Skill that lets AI agents control any Android phone via ADB + [uiautomator2](https://github.com/openatx/uiautomator2). The AI reads the UI tree, decides what to tap/type/swipe, and verifies the result — all through a single CLI tool.

## Features

- **Full phone control** — tap, type (CJK supported), swipe, scroll, lock/unlock, screenshot
- **AI-optimized output** — numbered UI dump as compact JSON; scroll hints as `[重要提示]` before JSON
- **Token efficient** — multiple dump modes (interactive, numbered, search, diff) to minimize context usage
- **Safety built-in** — payment screen detection, sensitive keyword blocking, operation audit log
- **Self-healing** — auto-reconnect, agent restart, popup auto-dismiss via watchers
- **Batch execution** — `batch-steps` runs multiple actions in one call to save round-trips

## How It Works

```
AI Agent ──→ ./phone ui dump --interactive --numbered
         ←── [重要提示] 纵向可滚动(ViewPager)...
              {"package":"com.tencent.mm","elements":[{"index":1,"class":"TextView","text":"微信",...}]}

AI Agent ──→ ./phone input tap-nth 3
         ←── {"status":"ok","data":["Tapped #3 at (360,400)"]}
```

1. AI calls `ui dump` to see the screen as structured JSON
2. AI picks an element by index and calls `tap-nth`, `tap-text`, or `input text`
3. AI re-dumps to verify the result
4. All commands output JSON by default (use `--plain` for text)

## Prerequisites

### Host Machine (macOS / Linux)

```bash
brew install android-platform-tools   # or: apt install adb
pip install uiautomator2 lxml Pillow PyYAML
```

### Android Phone

1. Enable **Developer Options** (Settings → About Phone → tap Build Number 7 times)
2. Enable **USB Debugging**
3. For ColorOS/MIUI: also enable **USB Debugging (Security Settings)**
4. First-time setup via USB:
   ```bash
   adb devices                    # verify connection
   python -m uiautomator2 init    # install ATX agent on phone
   ```

## Quick Start

```bash
# Setup: copy config template
cp config.yaml.example config.yaml

# Check connection
./phone status

# View screen (AI's primary command)
./phone ui dump --interactive --numbered

# Tap by index from dump
./phone input tap-nth 3

# Tap by visible text
./phone input tap-text "搜索"

# Type text (CJK supported)
./phone input text "Hello 你好"

# Launch app
./phone app launch com.tencent.mm

# Screenshot
./phone screenshot
```

## JSON Output

All commands output JSON by default. Two formats:

**UI Dump** (custom format with scroll hints):
```
[重要提示] 纵向可滚动(ViewPager)，当前仅显示可见部分。如需查看更多: 'input swipe 360 1069 360 356'。
{"package":"com.tencent.mm","activity":".ui.LauncherUI","screen":{"width":720,"height":1604},"elements":[...]}
```

**All other commands** (standard wrapper):
```json
{"status":"ok","command":"input tap-text","timestamp":"2026-03-04T02:35:00","duration_ms":1250,"data":["Tapped \"搜索\" at (540,200)"]}
```

## WiFi ADB (Optional)

```bash
adb tcpip 5555
adb connect <phone-ip>:5555
# Then edit config.yaml: device: "<phone-ip>:5555", mode: "wifi"
```

## Project Structure

```
adb-agent/
├── SKILL.md                 # AI operation manual (loaded by OpenClaw)
├── phone                    # Wrapper script (auto-activates venv)
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
- Device connection (USB / WiFi)
- Timeouts
- Sensitive packages and keywords
- Screen dimensions

## License

MIT
