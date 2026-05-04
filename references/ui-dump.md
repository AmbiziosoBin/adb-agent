# UI Dump Guide

## Overview

`ui dump` is the core command for viewing phone screen content. It returns the current screen's UI structure, including all interactive elements' positions, text, and attributes.

## Basic Usage

```bash
# Most common: interactive numbered dump
./phone ui dump --interactive --numbered

# Quick check (only package/activity)
./phone ui current

# Search for specific text
./phone ui dump --search "下载" --numbered

# Increase timeout (when UI loads slowly)
./phone ui dump --timeout 30
```

---

## Output Format

### Full Output Structure

```
[重要提示] 纵向可滚动(ViewPager)，当前仅显示可见部分。如需查看更多: 'input swipe 360 1069 360 356'。信息流应用避免死循环，最多滚动1-2次。
{"package":"com.tencent.mm","activity":".ui.LauncherUI","screen":{"width":720,"height":1604},"elements":[{"index":1,"class":"TextView","text":"微信","center":[72,120],"clickable":true},{"index":2,"class":"EditText","desc":"搜索","center":[360,200],"clickable":true}]}
```

**Two parts**:
1. **Scroll hints** (`[重要提示]`) — text lines, appear BEFORE JSON
2. **JSON data** — structured UI information

---

## Scroll Hints `[重要提示]`

### Purpose

Tells you whether the page has hidden content and provides ready-to-use swipe commands.

### Examples

**Vertical scrolling**:
```
[重要提示] 纵向可滚动(ViewPager)，当前仅显示可见部分。如需查看更多: 'input swipe 360 1069 360 356'。信息流应用避免死循环，最多滚动1-2次。
```

**Horizontal scrolling**:
```
[重要提示] 横向可滚动(HorizontalScrollView)，右侧可能有隐藏按钮。如需查看: 'input swipe 648 400 72 400'
```

**Not scrollable**:
```
[重要提示] 当前页面不可滚动，已显示全部内容
```

### How to Use

1. **Read hints first** — before parsing JSON, check `[重要提示]`
2. **Copy commands** — directly copy the `input swipe` command from hints
3. **Avoid infinite loops** — for feed apps, scroll max 1-2 times

---

## JSON Field Reference

### Root Fields

| Field | Type | Description | Example |
|-------|------|-------------|--------|
| `package` | string | Current app package name | `"com.tencent.mm"` |
| `activity` | string | Current Activity | `".ui.LauncherUI"` |
| `screen` | object | Screen dimensions | `{"width":720,"height":1604}` |
| `screenOn` | boolean | Whether screen is on (only when false) | `false` |
| `elements` | array | All interactive elements | `[...]` |

### Element Fields

Each element object contains:

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `index` | number | ✅ | Element index (for `tap-nth`) |
| `class` | string | ✅ | Android class name |
| `text` | string | ✅ | Element text (android:text), may be empty |
| `desc` | string | ✅ | Content description (content-desc), may be empty |
| `resourceId` | string | ❌ | Resource ID (only when present) |
| `center` | [x, y] | ✅ | Element center coordinates |
| `bounds` | string | ✅ | Boundary coordinates `"[x1,y1][x2,y2]"` |
| `clickable` | boolean | ✅ | Whether clickable (always present) |
| `scrollable` | boolean | ❌ | Whether scrollable (only when true) |
| `selected` | boolean | ❌ | Whether selected (only when true) |
| `checked` | boolean | ❌ | Whether checked (only when true) |
| `focused` | boolean | ❌ | Whether focused (only when true) |

### Example Element

```json
{
  "index": 5,
  "class": "Button",
  "text": "获取验证码",
  "desc": "",
  "resourceId": "com.app:id/btn_code",
  "center": [540, 1200],
  "bounds": "[400,1150][680,1250]",
  "clickable": true
}
```

---

## How to Use Dump Results

### 1. Tap by Index (recommended)

```bash
./phone ui dump --interactive --numbered
# See: {"index": 5, "text": "获取验证码", ...}
./phone input tap-nth 5
```

**Advantage**: 100% accurate, unaffected by text changes

### 2. Tap by Text

```bash
./phone ui dump --interactive --numbered
# See: {"text": "同意", ...}
./phone input tap-text "同意"
```

**Note**: Tool uses exact-match-first, `tap-text "同意"` will NOT hit "不同意"

### 3. Tap by Resource ID

```bash
./phone ui dump --interactive --numbered
# See: {"resourceId": "com.app:id/btn", ...}
./phone input tap-id "com.app:id/btn"
```

### 4. Tap by Coordinates

```bash
./phone ui dump --interactive --numbered
# See: {"center": [540, 1200], ...}
./phone input tap 540 1200
```

---

## Special Cases

### Element with `clickable: false`

**Meaning**: This is a label or container, not a button.

**Handling**:
- Don't try to click it
- If you need to click, find its parent or child element

**Example**:
```json
{"index": 3, "text": "张三", "clickable": false}  // This is a label
{"index": 4, "text": "", "clickable": true}        // This is the clickable container for "张三"
```

### Element with no `text` and `desc`

**Meaning**: This is an icon, image, or empty container.

**Handling**:
- Use `tap-nth` to tap by index
- Or use `tap` to tap by coordinates
- Cannot use `tap-text`

### `scrollable: true`

**Meaning**: This element is scrollable.

**Handling**:
- Execute `swipe` within this element's area
- Or use the command from scroll hints

---

## `--search` Filtering

### Usage

```bash
./phone ui dump --search "下载" --numbered
```

### Effect

Returns only elements containing "下载" text and nearby elements.

### Example

**Original dump** (100 elements):
```json
{"elements": [
  {"index": 1, "text": "首页", ...},
  {"index": 2, "text": "搜索", ...},
  ...
  {"index": 50, "text": "下载", ...},
  ...
  {"index": 100, "text": "设置", ...}
]}
```

**After filtering** (only relevant elements):
```json
{"elements": [
  {"index": 48, "text": "应用名称", ...},
  {"index": 49, "text": "版本 1.0", ...},
  {"index": 50, "text": "下载", ...},
  {"index": 51, "text": "详情", ...}
]}
```

### Notes

- `tap-nth` after `--search` still uses the filtered indexes
- Filtering is fuzzy (substring match)

---

## `ui current` vs `ui dump`

| Command | Output | Use Case | Token Cost |
|---------|--------|----------|------------|
| `ui current` | 5-line basic info | Quick app state check | Very low |
| `ui dump` | Full UI tree | View all elements, decide next action | Higher |

### `ui current` Output Example

```json
{
  "package": "com.tencent.mm",
  "activity": ".ui.LauncherUI",
  "screen": "on",
  "resolution": "720x1604",
  "battery": "100%"
}
```

**Can see**:
- Whether current app crashed
- Whether screen is on
- Which activity is active

**Cannot see**:
- Any UI elements (buttons, text, input fields)
- Cannot verify action results

---

## Best Practices

### 1. Always dump before acting

```bash
# ✓ Correct
./phone ui dump --interactive --numbered
./phone input tap-nth 5

# ✗ Wrong: clicking without dump
./phone input tap-text "确定"  # Element may not exist
```

### 2. Re-dump after actions to verify

```bash
./phone input tap-text "获取验证码"
./phone ui dump --interactive --numbered  # Check if button changed to countdown
```

### 3. Don't use `ui current` to verify action results

```bash
# ✗ Wrong
./phone input tap-text "获取验证码"
./phone ui current  # Only shows package/activity, not button state

# ✓ Correct
./phone input tap-text "获取验证码"
./phone ui dump --interactive --numbered  # Can see if button text changed
```

### 4. Dumps are snapshots — indexes change after actions

```bash
# ✗ Wrong
./phone ui dump --interactive --numbered  # Index 5 is "确定"
./phone input tap-text "取消"             # After click, popup closes
./phone input tap-nth 5                   # Index changed! May tap wrong element

# ✓ Correct
./phone ui dump --interactive --numbered
./phone input tap-text "取消"
./phone ui dump --interactive --numbered  # Re-dump
./phone input tap-nth <new_index>
```

### 5. Use `--search` to save tokens

```bash
# If page has 100 elements but you only care about "下载" related
./phone ui dump --search "下载" --numbered
```

---

## FAQ

### Q1: Dump returns empty elements array
**A**: Possible causes:
- Screen off/locked → `./phone device screen-on`
- UI still loading → wait or increase `--timeout`
- uiautomator2 crashed → `./phone device restart-agent`

### Q2: Can't find an element that clearly exists
**A**: Possible causes:
- Element is off-screen (need to scroll)
- Element is an image/icon (no text or desc) → use `tap-nth`
- Element is hidden behind a popup → handle popup first

### Q3: How to click an element with `clickable: false`?
**A**:
- Find its parent element (usually the parent has clickable=true)
- Or tap by coordinates directly: `./phone input tap <x> <y>`

### Q4: Dump is too slow?
**A**:
- Use `--search` to filter
- Use `ui current` for quick checks (when full UI isn't needed)
- Check network/USB connection
