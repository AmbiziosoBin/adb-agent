---
name: adb-agent
description: Control an Android phone via ADB and uiautomator2. Use when the user asks to operate their phone, open apps, tap buttons, type text, scroll, take screenshots, install/uninstall apps, adjust settings, lock/unlock screen, send messages, make calls, or any other phone interaction. Also use when the user says "帮我用手机..." / "在手机上..." / "打开手机..." / "手机帮我..."
metadata:
  {
    "openclaw": {
      "emoji": "📱",
      "os": ["darwin", "linux", "win32"],
      "requires": { "bins": ["adb", "python3"] }
    }
  }
---

# Android Phone Control

Control an Android phone via ADB + uiautomator2 using `phone_control.py`.

## When to Use

**USE** when user asks to operate phone, open apps, tap/type/scroll, install apps, adjust settings, lock/unlock, screenshot, send messages, make calls, check status, or says "帮我.../在手机上.../用手机.../打开..."

## Setup

All commands use the `phone` wrapper script in this skill directory, which auto-activates the Python venv.

Working directory for all commands: `~/.openclaw/workspace/skills/adb-agent`

## Quick Start

```bash
./phone status                              # check connection
./phone ui dump --interactive --numbered    # view screen (ALWAYS first)
./phone input tap-nth 3                     # tap by index from dump
./phone input tap-text "搜索"                # tap by text
./phone input tap-text "搜索" --index 2     # tap 2nd match
./phone input text "你好世界"               # type text (Chinese OK)
./phone app launch com.tencent.mm           # launch app
./phone input key BACK                      # back / home
./phone ui current                          # quick check (saves tokens)
./phone screenshot                          # screenshot (send to user via MEDIA:)
./phone --plain input tap-text "确定"       # --plain for text output (JSON is default)
```

## Operating Principles

**🔴 CRITICAL: Screenshot on key steps** — Call `./phone screenshot` in THREE scenarios:
1. **After app launch** — verify the app opened correctly
2. **After task completion** — show final result to user
3. **When user confirmation needed** — popups, CAPTCHAs, unexpected screens

The command outputs `MEDIA:<path>` which automatically triggers OpenClaw to send the image to the user. You don't need to read or view the image yourself (saves tokens). Just call it and let OpenClaw handle the display.

1. **Look before act**: Always `ui dump --interactive --numbered` before operations
2. **Verify after action**: Re-dump to confirm success, check UI elements changed for critical actions
3. **Use app launch**: Don't go HOME and tap icons, use `./phone app launch <package>`
4. **Wait for loading**: Use `wait text` after launching apps
5. **batch-steps for known flows**: Avoid popup-triggering actions (see [batch-steps guide](references/batch-steps.md))
6. **CAPTCHA handling**: For slider/click CAPTCHAs, see [CAPTCHA guide](references/captcha.md)
7. **Dumps are snapshots**: Element indexes change after actions, always re-dump before `tap-nth`
8. **Screenshot auto-delivery**: `./phone screenshot` auto-sends via MEDIA:, don't `read` the file
9. **UI dump details**: For output format details, see [UI dump guide](references/ui-dump.md)
10. **Troubleshooting**: Check [troubleshooting guide](references/troubleshooting.md) or [commands reference](references/commands.md)

## Batch Steps (Multi-Step Operations)

When you already know the sequence of UI actions to perform, use `batch-steps` to execute them all in **one command**. This avoids multiple AI↔tool round-trips, saving time and tokens.

```bash
# Execute a multi-step login flow in one call:
./phone batch-steps '[{"action":"input","command":"tap-text","args":{"text":"手机号"}},{"action":"input","command":"text","args":{"content":"13800138000"}},{"action":"input","command":"tap-text","args":{"text":"同意"}},{"action":"input","command":"tap-text","args":{"text":"获取验证码"}}]'
```

**UI Change Auto-Detection**: batch-steps automatically detects unexpected UI changes (popups, dialogs, activity jumps) and interrupts execution. When interrupted, it outputs a warning before the JSON and includes the current UI snapshot in `current_ui` field for analysis.

**Key Points**:
- Each step: `{"action": "input/wait/app/ui/device/shell/sleep", "command": "tap-text/text/key/...", "args": {...}}`
- Options: `--delay 0.3`, `--stop-on-error`, `--verify`, `--no-ui-check`
- ⚠️ Avoid popup-triggering actions ("Get Code", "Submit", "Pay") in batch-steps

For complete JSON format, supported actions, and examples, see [batch-steps guide](references/batch-steps.md).

## UI Dump Output Format

`ui dump --interactive --numbered` outputs scroll hints (text) FIRST, then JSON:
- **Scroll hints** (`[重要提示]`): Read these first! They tell you if the page is scrollable and provide ready-to-use swipe commands
- **Element fields**: `index` (for tap-nth), `text`, `desc`, `center` [x,y], `clickable` (boolean), `scrollable`/`selected`/`checked` (when true)
- **Root fields**: `package`, `activity`, `screen` {width,height}

For detailed field descriptions and examples, see [UI dump guide](references/ui-dump.md).

## CAPTCHA Handling

⚠️ **When encountering CAPTCHAs, you MUST first read `references/captcha.md` for the complete workflow. Do NOT guess coordinates or try random swipes.**

CAPTCHA solving uses `scripts/captcha_solver.py` which calls a third-party recognition API. The AI only needs to:
1. Analyze CAPTCHA type and element positions from UI dump
2. Call `captcha_solver.py screenshot` to capture and submit for recognition
3. Execute swipe/tap based on recognition results

See [CAPTCHA guide](references/captcha.md) — **read this file first before any CAPTCHA operation**.

---

## Detailed Documentation Index

For specific scenarios and detailed guides, refer to:

- 📋 [Commands Reference](references/commands.md) — Complete command list and parameters
- 🎯 [Common Scenarios](references/scenarios.md) — Messaging, search, login examples
- 🔧 [Troubleshooting](references/troubleshooting.md) — Common errors and solutions
- 🤖 [CAPTCHA Guide](references/captcha.md) — Slider/click CAPTCHA complete workflow
- 📦 [Batch-Steps Guide](references/batch-steps.md) — Batch operations, UI change detection
- 🎨 [UI Dump Guide](references/ui-dump.md) — Dump output format, element fields

## Common Mistakes (DON'T DO THESE)

```bash
# ✗ WRONG: screenshot is a TOP-LEVEL command, not under device
./phone device screenshot

# ✓ CORRECT:
./phone screenshot
./phone screenshot --filename shot.png

# ✗ WRONG: reading the screenshot file (wastes tokens!)
./phone screenshot
read /Users/smnz/.openclaw/media/phone/screenshot_xxx.png

# ✓ CORRECT: screenshot auto-delivered via MEDIA: protocol
./phone screenshot

# ✗ WRONG: --index is for tap-text, not tap-nth
./phone input tap-nth 2 --search "搜索"

# ✓ CORRECT: use ui dump --search first, then tap-nth
./phone ui dump --search "搜索" --numbered
./phone input tap-nth 1

# ✗ WRONG: swipe with 5th positional arg
./phone input swipe 626 135 626 135 100

# ✓ CORRECT: use --duration flag
./phone input swipe 626 135 626 135 --duration 0.1

# ✗ WRONG: shell command needs quotes around the full command
./phone shell input tap 626 135

# ✓ CORRECT: wrap in quotes
./phone shell "input tap 626 135"

# ✗ WRONG: using stale text from old dump
./phone input tap-text "pubg aespa联名"   # text may have changed!

# ✓ CORRECT: re-dump first
./phone ui dump --interactive --numbered
./phone input tap-nth <N>
```

