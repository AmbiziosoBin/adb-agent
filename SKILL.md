---
name: adb-agent
description: Control an Android phone via ADB and uiautomator2. Use when the user asks to operate their phone, open apps, tap buttons, type text, scroll, take screenshots, install/uninstall apps, adjust settings, lock/unlock screen, send messages, make calls, or any other phone interaction. Also use when the user says "帮我用手机..." / "在手机上..." / "打开手机..." / "手机帮我..."
metadata:
  {
    "openclaw": {
      "emoji": "📱",
      "os": ["darwin"],
      "requires": { "bins": ["adb", "python3"] }
    }
  }
---

# Android Phone Control

Control an Android phone via ADB + uiautomator2 using `phone_control.py`.

## When to Use

**USE** when user asks to operate phone, open apps, tap/type/scroll, install apps, adjust settings, lock/unlock, screenshot, send messages, make calls, check status, or says "帮我.../在手机上.../用手机.../打开..."

**DON'T USE** for general Android knowledge questions, controlling other devices, or when OpenClaw Node native commands are better suited.

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
./phone screenshot                          # screenshot (top-level cmd)
./phone --plain input tap-text "确定"       # --plain for text output (JSON is default)
```

## Operating Principles

1. **Look before act**: ALWAYS `ui dump --interactive --numbered` before any operation
2. **Verify after action**: Re-dump to confirm the action worked
3. **Save tokens**: Use `--interactive --numbered`. Use `ui current` for quick checks
4. **Wait for loading**: Use `wait text` after launching apps
5. **Handle popups**: Dismiss with `tap-text "允许"` / `"同意"` / `"确定"`
6. **Safety first**: Tool auto-blocks payment screens. Never force-bypass
7. **Scroll to see more**: If `[重要提示]` lines appear BEFORE the JSON, read them first — they contain ready-to-use swipe commands. Horizontal = hidden buttons on right. For feeds, max 1-2 scrolls
8. **Read element booleans**: `"clickable":true` = tappable. Elements with `"clickable":false` are labels/containers. Also check `"scrollable"`, `"selected"`, `"checked"` when present
9. **Don't mix CLI flags**: `--search` belongs to `ui dump`, NOT `tap-nth`. `--index` belongs to `tap-text`
10. **Dumps are snapshots**: After any action, element indexes change. ALWAYS re-dump before `tap-nth`
11. **Submit search with ENTER**: Use `input key ENTER` after typing in search box
12. **tap-nth uses cached dump**: `tap-nth N` taps from the LAST `ui dump --numbered`, respecting `--search` filters
13. **Prefer tap-text over set-text**: Tap input field first, then `input text "content"`. Only use `set-text` to replace existing text
14. **batch-steps for known flows**: Execute multiple steps in one call to save round-trips
15. **All commands output JSON by default**: No need for `--json`. Use `--plain` to get text output if needed
16. **Screenshot auto-delivery**: `./phone screenshot` auto-sends to user via MEDIA: protocol. Do NOT `read` the file
17. **Proactive screenshot**: Take screenshots after completing tasks, on unexpected screens, popups/CAPTCHAs, at key checkpoints, or when results don't match expectations. Image is auto-delivered.
18. **Slider/Click CAPTCHA playbook**: If screen shows "拖动滑块" / "请通过以下验证" / slider CAPTCHA:

    **Step 1 — Screenshot & analyze**:
    ```bash
    ./phone screenshot
    ```
    Study the screenshot to identify:
    - Slider button center coordinates (x1, y1) — the draggable handle
    - Target gap/destination coordinates (x2, y2) — where to drag to
    - Note: y1 and y2 are usually the same (horizontal slider)

    **Step 2 — Execute human-like swipe** using `captcha-swipe` (NOT plain `swipe`):
    ```bash
    ./phone input captcha-swipe <x1> <y1> <x2> <y2> \
      --duration 0.8 \
      --easing human \
      --hold-start 0.12 \
      --hold-end 0.08 \
      --overshoot 8 \
      --y-wobble 3 \
      --steps 30 \
      --verify \
      --wait-after 1.5
    ```

    **Parameter tuning guide** (adjust these between retries):
    | Parameter | Range | Effect |
    |-----------|-------|--------|
    | `--duration` | 0.5–2.0s | Total movement time. Too fast = bot-like; too slow = timeout |
    | `--easing` | human/ease-in-out/linear | `human` adds natural speed variation + noise |
    | `--hold-start` | 0.05–0.3s | Finger press-and-hold before moving. Mimics human reaction |
    | `--hold-end` | 0.03–0.2s | Pause before releasing. Mimics human settling |
    | `--overshoot` | 0–15px | Slide past target then settle back. Mimics inertia |
    | `--y-wobble` | 0–5px | Vertical finger deviation during drag. Mimics hand tremor |
    | `--steps` | 15–60 | Path smoothness. More = smoother trajectory |

    **Step 3 — Check result**:
    - `--verify` flag auto-checks UI for success/failure keywords after the swipe
    - If UNCERTAIN, take another screenshot to visually confirm

    **Step 4 — Retry logic** (MAX 3 ATTEMPTS):
    - ⚠️ **IMPORTANT**: After each failed attempt, the CAPTCHA gap/image typically REFRESHES to a new position. You MUST take a fresh screenshot before retrying to get the new target coordinates.
    - On retry, vary parameters: try different `--duration` (±0.3s), `--overshoot` (0→10→5), `--easing` (human→ease-in-out)
    - After 3 failed attempts, **ASK THE USER**: "CAPTCHA failed 3 times. Continue?" — script auto-screenshots on failure so user can see the screen.

## Batch Steps (Multi-Step Operations)

When you already know the sequence of UI actions to perform, use `batch-steps` to execute them all in **one command**. This avoids multiple AI↔tool round-trips, saving time and tokens.

```bash
# Execute a multi-step login flow in one call:
./phone batch-steps '[{"action":"input","command":"tap-text","args":{"text":"手机号"}},{"action":"input","command":"text","args":{"content":"13800138000"}},{"action":"input","command":"tap-text","args":{"text":"同意"}},{"action":"input","command":"tap-text","args":{"text":"获取验证码"}}]'
```

### batch-steps JSON Format

Input is a JSON array. Each step object:

| Field | Required | Description |
|-------|----------|-------------|
| `action` | ✅ | Command category: `input`, `wait`, `app`, `ui`, `device`, `shell`, `sleep` |
| `command` | ✅ | Subcommand: `tap-text`, `text`, `key`, `tap`, `tap-id`, `tap-nth`, `swipe-dir`, `clear`, `set-text`, `launch`, `stop`, `dump`, `screen-on`, `unlock` |
| `args` | ✅ | Dict of arguments for the subcommand |
| `description` | ❌ | Human-readable step label (for logging) |
| `verify_text` | ❌ | Text to check exists after step completes |

### batch-steps Options

- `--delay 0.3` — Delay between steps (default 0.3s)
- `--stop-on-error` — Stop on first error (default)
- `--no-stop-on-error` — Continue even if a step fails
- `--verify` — Verify UI state after each step

### batch-steps Output (always JSON)

```json
{
  "status": "ok",
  "command": "batch-steps",
  "timestamp": "2026-03-02T21:30:00",
  "duration_ms": 4500,
  "total_steps": 4,
  "completed": 4,
  "failed": 0,
  "steps": [
    {"step": 1, "status": "ok", "duration_ms": 1200, "description": "input tap-text", "result": "..."},
    {"step": 2, "status": "ok", "duration_ms": 800, "description": "input text", "result": "..."},
    {"step": 3, "status": "ok", "duration_ms": 500, "description": "input tap-text", "result": "..."},
    {"step": 4, "status": "ok", "duration_ms": 2000, "description": "input tap-text", "result": "..."}
  ]
}
```

### When to Use batch-steps vs Single Commands

- **Use batch-steps** when: you already see the full UI from a dump and know the exact sequence (login, search, form fill, dismiss dialogs)
- **Use single commands** when: you need to see UI state after each action to decide the next step (exploring unknown screens, debugging)

### batch-steps Supported Actions & Args Quick Reference

| action | command | args |
|--------|---------|------|
| `input` | `tap-text` | `{"text": "确定", "index": 1}` |
| `input` | `tap` | `{"x": 540, "y": 1200}` |
| `input` | `tap-id` | `{"resource_id": "com.app:id/btn"}` |
| `input` | `tap-nth` | `{"n": 3}` |
| `input` | `text` | `{"content": "hello"}` |
| `input` | `set-text` | `{"selector": "搜索", "content": "keyword"}` |
| `input` | `key` | `{"keycode": "ENTER"}` |
| `input` | `swipe-dir` | `{"direction": "down", "distance": 0.5}` |
| `input` | `clear` | `{}` |
| `input` | `captcha-swipe` | `{"x1": 150, "y1": 900, "x2": 650, "y2": 900, "duration": 0.8, "easing": "human", "overshoot": 8, "y_wobble": 3, "verify": true}` |
| `wait` | `text` | `{"text": "加载完成", "timeout": 10}` |
| `wait` | `gone` | `{"text": "加载中", "timeout": 10}` |
| `app` | `launch` | `{"package": "com.tencent.mm"}` |
| `app` | `stop` | `{"package": "com.tencent.mm"}` |
| `ui` | `dump` | `{}` (refreshes numbered cache) |
| `device` | `screen-on` | `{}` |
| `device` | `unlock` | `{}` |
| `shell` | (any) | `{"command": "input tap 100 200"}` |
| `sleep` | (seconds) | `{"seconds": 2}` |

## Numbered Dump Output Format

`ui dump --interactive --numbered` outputs scroll hints as text FIRST, then JSON:

```
[重要提示] 纵向可滚动(ViewPager)，当前仅显示可见部分。如需查看更多: 'input swipe 360 1069 360 356'。信息流应用避免死循环，最多滚动1-2次。
{"package":"com.tencent.mm","activity":".ui.LauncherUI","screen":{"width":720,"height":1604},"elements":[{"index":1,"class":"TextView","text":"微信","center":[72,120],"clickable":true},{"index":2,"class":"EditText","desc":"搜索","center":[360,200],"clickable":true},{"index":3,"class":"TextView","text":"张三","center":[300,400],"clickable":false}]}
```

**Scroll hints** (`[重要提示]`) appear BEFORE JSON — read them first! They tell you whether the page has hidden content and provide ready-to-use swipe commands.

**Element fields**: `index` (for `tap-nth`), `class`, `text` (android:text), `desc` (content-desc), `resourceId` (fallback), `center` [x,y], `clickable` (always boolean), `scrollable`/`selected`/`checked` (only when true)

**Root fields**: `package`, `activity`, `screen` {width,height}, `screenOn` (only when false)

## Default JSON Output (All Other Commands)

All commands output JSON by default. Standard wrapper format:

```json
{"status":"ok","command":"input tap-text","timestamp":"2026-03-04T02:35:00","duration_ms":1250,"data":["Tapped \"搜索\" at (540,200)"]}
```

- `status` — `"ok"` or `"error"`
- `data` — array of output messages
- `error` — only on failure: `{"message":"...", "hint":"...", "cause":"..."}`
- Use `--plain` to get legacy text output

## Common Scenarios

### Search and Download App
```bash
./phone app launch com.tencent.android.qqdownloader
./phone wait text "搜索"
./phone input tap-text "搜索"
./phone input text "抖音"
./phone input key ENTER
./phone wait text "下载"
./phone ui dump --search "下载" --numbered
./phone input tap-nth 1                     # pick the right download button
```

### Send WeChat Message
```bash
./phone app launch com.tencent.mm
./phone wait text "微信"
./phone ui dump --interactive --numbered
./phone input tap-text "搜索"
./phone input text "张三"
./phone input tap-text "张三"
./phone wait text "发消息"
./phone input tap-text "发消息"
./phone input set-text "" "我晚点到"
./phone input tap-text "发送"
```

### Unlock / Scroll
```bash
./phone device screen-on && ./phone device unlock --swipe
./phone input swipe-dir down                # scroll down
./phone input scroll-to "设置"               # scroll until text found
./phone input swipe-dir left                # swipe left (switch tab)
```

## Error Handling

- **Device not found**: `./phone status`
- **UI dump timeout**: `./phone ui dump --timeout 30`
- **Text input fails**: `./phone device ime-setup`
- **Agent crashed**: `./phone device restart-agent`
- **Connection lost**: `./phone status`, check USB/WiFi

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

## Detailed References

- **All commands & parameters**: see `references/commands.md`
- **More scenario examples**: see `references/scenarios.md`
- **Troubleshooting guide**: see `references/troubleshooting.md`

## Performance Notes

- `batch-steps` eliminates AI↔tool round-trips for known flows
- Numbered dump outputs structured JSON directly, no extra parsing needed
- Wait polling interval is 0.5s for fast responsiveness
