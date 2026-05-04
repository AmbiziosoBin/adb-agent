# Batch-Steps Guide

## Overview

`batch-steps` executes multiple UI operations in a single command, avoiding multiple AI↔tool round-trips and saving time and tokens.

## When to Use

**✅ Use batch-steps**:
- You already see the full UI from `ui dump`
- You know the exact sequence of operations
- Operations won't trigger popups (see limitations below)

**Example scenarios**:
- Filling multiple form fields
- Dismissing a series of known popups
- Executing a fixed navigation flow

**❌ Don't use batch-steps**:
- You need to check UI state after each step to decide the next one
- Exploring unknown screens
- Debugging issues

---

## UI Change Auto-Detection

**Core feature**: `batch-steps` compares UI state before and after each step, automatically interrupting when unexpected changes are detected.

### Types of Changes Detected

1. **Activity jump** (unless the action was `app launch`)
2. **Popup/dialog** (keyword detection: 同意, 不同意, 允许, 拒绝, 确定, 取消, 协议, 条款, 隐私, 验证码, etc.)
3. **Major new elements** (>5 new text strings appeared)

### Output on Interruption

**Warning printed before JSON** (AI sees it immediately):
```
⚠️  BATCH-STEPS INTERRUPTED: Unexpected UI change detected (popup/dialog/screen change).
⚠️  AI should analyze current_ui in the JSON below and decide next action.
```

**JSON includes current UI snapshot**:
```json
{
  "status": "interrupted",
  "completed": 2,
  "failed": 0,
  "steps": [
    {"step": 1, "status": "ok", ...},
    {"step": 2, "status": "interrupted", "result": "... | UI change detected: Popup/dialog detected with keywords: 同意, 不同意"}
  ],
  "current_ui": {
    "package": "com.yek.android.kfc.activitys",
    "activity": "LoginBySmsCodeActivity",
    "texts": ["同意", "不同意", "用户协议", "隐私政策", ...],
    "elements": [...]
  }
}
```

### Disabling UI Detection

If you're certain there won't be popups, disable detection for better performance:
```bash
./phone batch-steps '[...]' --no-ui-check
```

---

## ⚠️ Important Limitations

**Do NOT include popup-triggering actions in batch-steps**:
- ❌ "Get verification code" (获取验证码)
- ❌ "Submit" (提交)
- ❌ "Pay" (支付)
- ❌ "Login" (登录) — may trigger terms/agreement popups

**Reason**: Even with UI detection, these should be handled separately to:
- Immediately see and handle popups
- Handle CAPTCHAs
- Confirm critical action results

**Correct approach**:
```bash
# ✓ Execute separately
./phone batch-steps '[{"action":"input","command":"tap-text","args":{"text":"手机号"}},{"action":"input","command":"text","args":{"content":"13800138000"}}]'
./phone input tap-text "获取验证码"  # Execute alone, may trigger popup
./phone ui dump --interactive --numbered  # Check for popups
```

---

## JSON Format

### Basic Structure

```json
[
  {
    "action": "input",
    "command": "tap-text",
    "args": {"text": "同意"},
    "description": "Tap agree button"
  },
  {
    "action": "input",
    "command": "text",
    "args": {"content": "13800138000"}
  }
]
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `action` | ✅ | Command category (see tables below) |
| `command` | ✅ | Subcommand (see tables below) |
| `args` | ✅ | Argument dictionary |
| `description` | ❌ | Step description (for logging) |
| `verify_text` | ❌ | Text to check exists after step completes |

---

## Supported Actions

### input Actions

| command | args | Description |
|---------|------|-------------|
| `tap-text` | `{"text": "确定", "index": 1}` | Tap by text |
| `tap` | `{"x": 540, "y": 1200}` | Tap by coordinates |
| `tap-id` | `{"resource_id": "com.app:id/btn"}` | Tap by resource ID |
| `tap-nth` | `{"n": 3}` | Tap by index from last dump |
| `text` | `{"content": "hello"}` | Type text |
| `set-text` | `{"selector": "搜索", "content": "keyword"}` | Replace text |
| `key` | `{"keycode": "ENTER"}` | Press key (BACK/HOME/ENTER/DELETE) |
| `swipe-dir` | `{"direction": "down", "distance": 0.5}` | Directional swipe |
| `swipe` | `{"x1": 100, "y1": 500, "x2": 100, "y2": 200, "duration": 0.5}` | Coordinate swipe |
| `clear` | `{}` | Clear current input field |
| `captcha-swipe` | `{"x1": 150, "y1": 900, "x2": 650, "y2": 900, "duration": 0.8, "easing": "human", "verify": true}` | CAPTCHA slider swipe |

### wait Actions

| command | args | Description |
|---------|------|-------------|
| `text` | `{"text": "加载完成", "timeout": 10}` | Wait for text to appear |
| `gone` | `{"text": "加载中", "timeout": 10}` | Wait for text to disappear |

### app Actions

| command | args | Description |
|---------|------|-------------|
| `launch` | `{"package": "com.tencent.mm"}` | Launch app |
| `stop` | `{"package": "com.tencent.mm"}` | Stop app |

### ui Actions

| command | args | Description |
|---------|------|-------------|
| `dump` | `{}` | Refresh UI dump cache |

### device Actions

| command | args | Description |
|---------|------|-------------|
| `screen-on` | `{}` | Turn on screen |
| `unlock` | `{}` | Unlock screen |

### Other Actions

| action | command | args | Description |
|--------|---------|------|-------------|
| `shell` | (any) | `{"command": "input tap 100 200"}` | Execute shell command |
| `sleep` | (seconds) | `{"seconds": 2}` | Wait specified seconds |

---

## CLI Options

```bash
./phone batch-steps '<json>' [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--delay 0.3` | 0.3 | Delay between steps (seconds) |
| `--stop-on-error` | true | Stop on first error |
| `--no-stop-on-error` | false | Continue even if a step fails |
| `--verify` | false | Verify UI state after each step |
| `--no-ui-check` | false | Disable UI change detection |

---

## Output Format

### Successful Completion

```json
{
  "status": "ok",
  "command": "batch-steps",
  "timestamp": "2026-03-04T06:30:00",
  "duration_ms": 4500,
  "total_steps": 4,
  "completed": 4,
  "failed": 0,
  "steps": [
    {"step": 1, "status": "ok", "duration_ms": 1200, "result": "..."},
    {"step": 2, "status": "ok", "duration_ms": 800, "result": "..."},
    {"step": 3, "status": "ok", "duration_ms": 500, "result": "..."},
    {"step": 4, "status": "ok", "duration_ms": 2000, "result": "..."}
  ]
}
```

### UI Change Detected

```
⚠️  BATCH-STEPS INTERRUPTED: Unexpected UI change detected (popup/dialog/screen change).
⚠️  AI should analyze current_ui in the JSON below and decide next action.

{
  "status": "interrupted",
  "completed": 2,
  "failed": 0,
  "steps": [
    {"step": 1, "status": "ok", ...},
    {"step": 2, "status": "interrupted", "ui_change": {"type": "popup_detected", "reason": "..."}}
  ],
  "current_ui": {...}
}
```

### Step Failure

```json
{
  "status": "partial",
  "completed": 2,
  "failed": 1,
  "steps": [
    {"step": 1, "status": "ok", ...},
    {"step": 2, "status": "ok", ...},
    {"step": 3, "status": "error", "result": "Element not found", "error": "..."}
  ]
}
```

---

## Complete Examples

### Example 1: Login Flow

```bash
./phone batch-steps '[
  {"action":"input","command":"tap-text","args":{"text":"手机号"},"description":"Tap phone number input"},
  {"action":"input","command":"text","args":{"content":"13800138000"}},
  {"action":"input","command":"key","args":{"keycode":"ENTER"}},
  {"action":"wait","command":"text","args":{"text":"验证码","timeout":5}}
]'
```

### Example 2: Search and Scroll

```bash
./phone batch-steps '[
  {"action":"input","command":"tap-text","args":{"text":"搜索"}},
  {"action":"input","command":"text","args":{"content":"抖音"}},
  {"action":"input","command":"key","args":{"keycode":"ENTER"}},
  {"action":"wait","command":"text","args":{"text":"下载","timeout":10}},
  {"action":"input","command":"swipe-dir","args":{"direction":"down","distance":0.5}}
]'
```

### Example 3: Dismiss Multiple Popups

```bash
./phone batch-steps '[
  {"action":"input","command":"tap-text","args":{"text":"允许"}},
  {"action":"sleep","command":"0.5"},
  {"action":"input","command":"tap-text","args":{"text":"同意"}},
  {"action":"sleep","command":"0.5"},
  {"action":"input","command":"tap-text","args":{"text":"确定"}}
]'
```

---

## Best Practices

1. **Dump before batch**: Always `ui dump` before batch-steps to confirm UI state
2. **Keep steps manageable**: Recommend max 10 steps per batch, longer batches are error-prone
3. **Critical actions separately**: Don't include "get code", "pay", etc. in batch
4. **Use description**: Add descriptions to each step for easier debugging
5. **Adjust delay**: If UI is slow to respond, increase `--delay`
6. **Verify key steps**: Use `verify_text` to confirm important steps succeeded

---

## FAQ

### Q1: batch-steps failed mid-way, how to continue?
**A**: batch-steps doesn't support resume from checkpoint. After failure:
1. Check which step failed
2. Re-`ui dump` to confirm current state
3. Build a new batch starting from the failed step

### Q2: How to debug batch-steps?
**A**:
- Use `--verify` flag
- Add `description` to each step
- After failure, check `result` and `error` in the `steps` array

### Q3: False positive on UI detection?
**A**:
- Check if there's actually a popup (look at `current_ui.texts`)
- If confirmed no issue, use `--no-ui-check` to disable detection
- Or adjust operation order to avoid triggering detection

### Q4: Can batch-steps be nested?
**A**: No. batch-steps doesn't support nesting; all steps must be flat.
