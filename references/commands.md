# Complete Command Reference

All commands use the format: `python3 phone_control.py <command> <subcommand> [options]`

Global options:
- `--device <serial>` — specify device (default: auto-detect)
- `--json` — output in JSON format (structured for AI parsing, includes timestamps and duration)

---

## UI Tree Operations (`ui`)

### `ui dump` — Dump UI hierarchy
```bash
ui dump                           # Default tree format
ui dump --interactive             # Only clickable/focusable/scrollable elements
ui dump --text                    # Only elements with text content
ui dump --numbered                # Number elements for tap-nth
ui dump --interactive --numbered  # ★ Most useful: numbered interactive elements
ui dump --package <pkg>           # Filter by package name
ui dump --depth <n>               # Limit tree depth
ui dump --search <keyword>        # Search for keyword in text/id/desc
ui dump --rect x1,y1,x2,y2       # Only elements in region
ui dump --timeout <seconds>       # Custom timeout (default 15s)
```

Flags can be combined: `ui dump --interactive --numbered --search "下载"`

### `ui find <type> <value>` — Find single element
```bash
ui find text "搜索"               # Find by text
ui find id "com.foo:id/search"    # Find by resource-id
ui find class "EditText"          # Find by class name
ui find desc "返回"               # Find by content-desc
```
Returns: class, text, desc, id, bounds, center coordinates, clickable state

### `ui exists <type> <value>` — Check element existence
```bash
ui exists text "登录"             # Returns: true / false
ui exists id "submit_btn"
```

### `ui current` — Quick current state (lightweight, saves tokens)
```bash
ui current
```
Returns: package, activity, screen state, resolution, battery

### `ui watch` — Monitor UI changes
```bash
ui watch --duration 15            # Watch for 15 seconds
```

### `ui diff` — Compare with last dump
```bash
ui diff                           # Shows added/removed elements since last dump
```

---

## Input Control (`input`)

### Tap
```bash
input tap <x> <y>                 # Tap coordinates
input tap-text "按钮文字"          # Tap by text content
input tap-text "搜索" --index 2   # Tap the 2nd element matching "搜索"
input tap-id "resource_id"        # Tap by resource-id
input tap-desc "描述"              # Tap by content-desc
input tap-nth <N>                 # Tap Nth element from numbered dump
```

### Long Press / Double Tap
```bash
input long-tap <x> <y> --duration 2.0    # Long press (default 1s)
input double-tap <x> <y>                  # Double tap
```

### Swipe
```bash
input swipe <x1> <y1> <x2> <y2> --duration 0.5    # Swipe between points
input swipe-dir up                                   # Swipe up (scroll down)
input swipe-dir down                                 # Swipe down (scroll up)
input swipe-dir left                                 # Swipe left
input swipe-dir right                                # Swipe right
input swipe-dir up --distance 0.8                    # Longer swipe
input scroll-to "目标文字" --max-scrolls 10          # Scroll until text found
```

### Text Input
```bash
input text "Hello 你好"           # Type text (supports Chinese)
input set-text "搜索框" "内容"     # Set text on specific field
input clear                       # Clear focused input
input clear "search_box"          # Clear specific input
```

### Keys
```bash
input key BACK                    # Back button
input key HOME                    # Home button
input key ENTER                   # Enter/confirm
input key VOLUME_UP               # Volume up
input key VOLUME_DOWN             # Volume down
input key POWER                   # Power button
input key MENU                    # Menu button
input key RECENT_APPS             # Recent apps
input key CAMERA                  # Camera button
input key SEARCH                  # Search
input key DELETE                  # Backspace/delete
```

### Gestures
```bash
input pinch in --scale 0.5        # Pinch in (zoom out)
input pinch out --scale 0.5       # Pinch out (zoom in)
input drag <x1> <y1> <x2> <y2> --duration 0.5    # Drag
input multi-tap "100,200" "300,400"                # Multi-point tap
input gesture "100,800" "200,600" "300,400"        # Custom gesture path
```

### CAPTCHA Slider Swipe
Human-like swipe designed for CAPTCHA slider verification. AI controls all parameters.

```bash
# Full parameter example:
input captcha-swipe <x1> <y1> <x2> <y2> \
  --duration 0.8 \
  --easing human \
  --hold-start 0.12 \
  --hold-end 0.08 \
  --overshoot 8 \
  --y-wobble 3 \
  --steps 30 \
  --verify \
  --wait-after 1.5

# Minimal (uses smart defaults):
input captcha-swipe 150 900 650 900 --verify
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `x1 y1` | required | Slider button center (start) |
| `x2 y2` | required | Target gap position (end) |
| `--duration` | 0.8 | Movement duration in seconds |
| `--easing` | human | Speed curve: `linear`, `ease-in`, `ease-out`, `ease-in-out`, `human` |
| `--hold-start` | 0.12 | Hold at start before moving (seconds) |
| `--hold-end` | 0.08 | Hold at end before releasing (seconds) |
| `--overshoot` | 0 | Pixels to overshoot past target then settle back |
| `--y-wobble` | 0 | Max vertical deviation in pixels during drag |
| `--steps` | 30 | Number of intermediate path points (5–60) |
| `--verify` | off | Auto-check UI for CAPTCHA pass/fail after swipe |
| `--wait-after` | 1.5 | Seconds to wait before verification check |

Easing modes:
- `human` — Ease-in-out with slight random noise (most natural)
- `ease-in-out` — Smooth S-curve acceleration/deceleration
- `ease-in` — Start slow, end fast
- `ease-out` — Start fast, end slow
- `linear` — Constant speed (least natural)

Also supported in batch-steps:
```json
{"action":"input","command":"captcha-swipe","args":{"x1":150,"y1":900,"x2":650,"y2":900,"duration":0.8,"easing":"human","overshoot":8,"y_wobble":3,"verify":true}}
```

---

## Device Control (`device`)

### Screen
```bash
device info                       # Full device info
device screen-on                  # Wake screen
device screen-off                 # Sleep screen
device is-screen-on               # Check: true/false
device lock                       # Lock screen
device unlock --swipe             # Swipe unlock
device unlock --pin 1234          # PIN unlock
device unlock --password abc123   # Password unlock
device unlock --pattern "x1,y1,x2,y2,..."  # Pattern unlock
```

### Display
```bash
device rotate auto                # Enable auto-rotation
device rotate 0                   # Portrait
device rotate 90                  # Landscape
device brightness 128             # Set brightness (0-255)
device brightness auto            # Auto brightness
device stay-awake on              # Don't sleep while charging
device stay-awake off
```

### Volume
```bash
device volume media up
device volume media down
device volume media set 10
device volume media mute
device volume ring set 5
device volume alarm set 8
device volume notification mute
```

### Connectivity
```bash
device wifi on / off / status
device wifi connect "SSID" --wifi-password "pass"
device bluetooth on / off / status
device airplane on / off / status
device mobile-data on / off / status
device hotspot on / off
device nfc on / off / status
device gps on / off / status
device dnd on / off                # Do not disturb
```

### Battery & System
```bash
device battery                    # Detailed battery info
device reboot --confirm           # Reboot (requires --confirm)
device reboot --confirm --recovery
device reboot --confirm --bootloader
```

### IME & Agent
```bash
device ime list                   # List input methods
device ime current                # Current IME
device ime set <ime_id>           # Set IME
device ime-setup                  # Setup FastInputIME for u2
device ime-restore [ime_id]       # Restore original IME
device check-a11y                 # Check accessibility service
device restart-agent              # Restart u2 ATX Agent
```

---

## App Management (`app`)

```bash
app list                          # All apps
app list --third-party            # Third-party only
app list --system                 # System only
app list --search "微信"          # Search
app info <package>                # Detailed info
app launch <package>              # Launch app
app launch <package> --activity <Activity>
app stop <package>                # Force stop
app stop-all                      # Stop all third-party apps
app install <path_or_url>         # Install APK
app uninstall <package> --confirm # Uninstall (requires --confirm)
app uninstall <package> --confirm --keep-data
app clear <package> --confirm     # Clear data (requires --confirm)
app current                       # Current foreground app
app recent                        # Recent apps
app permissions <package>         # List permissions
app permissions <package> --grant READ_CONTACTS
app permissions <package> --revoke CAMERA
app running                       # Running apps
app size <package>                # Storage usage
app disable <package>             # Disable
app enable <package>              # Enable
```

### Common Package Names
| App | Package |
|-----|---------|
| WeChat | com.tencent.mm |
| QQ | com.tencent.mobileqq |
| Alipay | com.eg.android.AlipayGphone |
| Taobao | com.taobao.taobao |
| Douyin | com.ss.android.ugc.aweme |
| Xiaohongshu | com.xingin.xhs |
| Bilibili | tv.danmaku.bili |
| App Store (OPPO) | com.oppo.market |
| App Store (Xiaomi) | com.xiaomi.market |
| Settings | com.android.settings |
| Camera (AOSP) | com.android.camera2 |
| Phone | com.android.dialer |
| Messages | com.android.mms |
| Chrome | com.android.chrome |
| Files | com.android.documentsui |

---

## File & Screenshot (`file`, `screenshot`, `screenrecord`)

```bash
file push local.txt /sdcard/        # Push to phone
file pull /sdcard/file.txt          # Pull from phone
file pull /sdcard/file.txt local.txt
file ls /sdcard/ --detail           # List directory
file rm /sdcard/temp.txt --confirm  # Delete (requires --confirm)
file mkdir /sdcard/mydir            # Create directory
file cat /sdcard/notes.txt          # View file
file stat /sdcard/file.txt          # File info

screenshot                          # Save screenshot
screenshot --filename shot.png
screenshot --quality 50
screenshot --element "搜索框"       # Element screenshot

screenrecord start --duration 30    # Start recording (max 30s)
screenrecord stop                   # Stop and pull file
```

---

## System Info (`sys`)

```bash
sys processes --top 10              # Top processes
sys memory                          # Memory usage
sys storage                         # Storage usage
sys cpu                             # CPU info
sys network                         # Network status
sys props                           # All system properties
sys props "model"                   # Search properties
sys logcat --lines 20               # Recent logs
sys logcat --app com.tencent.mm     # App-specific logs
sys logcat --level error            # Error logs only
sys notifications                   # List notifications
sys notifications --clear           # Clear all
sys settings system get screen_brightness
sys settings secure get default_input_method
sys settings global put airplane_mode_on 0
sys date                            # Current date/time
sys uptime                          # Uptime
sys thermal                         # Temperature
```

---

## Communication (`call`, `sms`, `contacts`)

```bash
call dial 13800138000               # Make call
call end                            # Hang up
call accept                         # Accept incoming

sms send 13800138000 "Hello"        # Compose SMS
sms read --count 5                  # Read recent SMS
sms read --from 10086               # SMS from specific number

contacts list                       # List contacts
contacts list --search "张三"
contacts add "张三" "13800138000"
contacts add "张三" "13800138000" "zhang@email.com"
contacts delete "张三"
```

---

## Media (`media`)

```bash
media play-pause                    # Toggle play/pause
media next                          # Next track
media prev                          # Previous track
media stop                          # Stop playback
media camera photo                  # Open camera (photo)
media camera video                  # Open camera (video)
media gallery --recent 5            # Recent media files
media record-audio start            # Start audio recording
media record-audio stop             # Stop recording
```

---

## Automation (`wait`, `assert`, `shell`, `intent`, `watcher`, etc.)

### Wait & Assert
```bash
wait text "加载完成" --timeout 15   # Wait for text
wait gone "加载中" --timeout 10     # Wait for text to disappear
wait activity ".MainActivity" --timeout 10

assert text "登录成功"              # Assert text exists (exit 1 if not)
assert not-text "错误"              # Assert text absent
```

### Shell & Intent
```bash
shell "pm list packages"            # Raw adb shell
intent android.intent.action.VIEW --data "https://example.com"
intent android.intent.action.SEND --package com.tencent.mm --extra text="Hello"
```

### Clipboard
```bash
clipboard get                       # Read clipboard
clipboard set "复制的内容"           # Set clipboard
```

### Open
```bash
open-url "https://example.com"      # Open in browser
open-settings                       # Open Settings
open-settings wifi                  # Open WiFi settings
open-settings bluetooth             # Open Bluetooth settings
open-settings display               # Open Display settings
open-settings developer             # Open Developer options
```

### Watcher (Auto popup handling)
```bash
watcher add allow_perm --when text "允许" --do click     # Auto-click "允许"
watcher add dismiss_ad --when text "跳过" --do click     # Auto-click "跳过"
watcher add back_popup --when text "广告" --do back      # Auto-press back
watcher remove allow_perm                                 # Remove specific
watcher remove --all                                      # Remove all
watcher list                                              # List active
```

### Toast
```bash
toast                               # Get recent toast message
```

### Location Mock
```bash
location mock 39.9042 116.4074      # Mock GPS (Beijing)
location mock-stop                  # Stop mocking
```

### Batch & Sleep
```bash
batch commands.txt                  # Execute commands from file
sleep 3                             # Wait 3 seconds
```

### Batch Steps (AI Multi-Step Operations)
```bash
# Execute multiple steps in one call (JSON input)
batch-steps '<json_array>'                        # Inline JSON
batch-steps steps.json                            # From file
batch-steps '<json>' --delay 0.5                  # Custom delay between steps
batch-steps '<json>' --no-stop-on-error           # Continue on error
batch-steps '<json>' --verify                     # Verify UI after each step
```

JSON format — array of step objects:
```json
[
  {"action": "input", "command": "tap-text", "args": {"text": "确定"}, "description": "Tap confirm"},
  {"action": "input", "command": "text", "args": {"content": "13800138000"}},
  {"action": "wait", "command": "text", "args": {"text": "验证码", "timeout": 10}},
  {"action": "input", "command": "key", "args": {"keycode": "ENTER"}},
  {"action": "sleep", "command": "2", "args": {"seconds": 2}}
]
```

Supported actions: `input`, `wait`, `app`, `ui`, `device`, `shell`, `sleep`

Output is always JSON with per-step status and timing.

### Macro
```bash
macro record my_flow                # Create macro file
macro play my_flow                  # Execute macro
macro list                          # List saved macros
macro delete my_flow                # Delete macro
```

---

## Notification (`notification`)

```bash
notification list --count 10        # List notifications
notification tap 0                  # Tap first notification
notification reply 0 "好的"         # Reply to notification
notification dismiss 0              # Dismiss specific
notification dismiss --all          # Dismiss all
notification expand                 # Open notification shade
notification collapse               # Close notification shade
```

---

## Health & Safety (`status`, `safety`)

```bash
status                              # ★ Comprehensive health check
status --force                      # Skip cache
health                              # Alias for status

safety check                        # Check current screen safety
safety audit --lines 20             # View audit log
```

---

## IME Management (`ime`)

```bash
ime detect                          # Show current IME
ime switch                          # Switch to FastInputIME
ime switch --keep-ime               # Skip (manual IME management)
ime restore                         # Restore original IME
ime restore com.sohu.inputmethod.sogou/.SogouIME
```

---

## Node Native Command Overlap

These features overlap with OpenClaw Node native commands. Prefer Node commands when available:

| Feature | This tool (ADB/u2) | Node native |
|---------|-------------------|-------------|
| Camera snap | `media camera photo` | `camera.snap` ★ |
| SMS send | `sms send` | `sms.send` ★ |
| Location | `location mock` | `location.get` ★ |
| Device status | `device info` | `device.status` ★ |
| Notifications | `notification list` | `notifications.list` ★ |

★ = Preferred when available

**Always use this tool for**: UI operations, app install/uninstall, system settings, screen control, text input, scrolling, gestures — these cannot be done via Node commands.
