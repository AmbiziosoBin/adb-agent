"""Input control: tap, swipe, text input, keys, gestures."""

import time
import re
import math
import random
from lxml import etree

from .connection import get_device
from .utils import output, error, ok, audit_log
from .ui import _get_ui_xml, _parse_xml, _get_node_attrs, _parse_bounds_str, _collect_interactive_nodes, _is_interactive, get_cached_numbered_node, get_cached_numbered_count
from . import config as cfg


def _find_element_by_text(device, text, index=1):
    """Find element center by text content. Prioritize clickable elements.
    
    Args:
        index: Which match to return (1=first, 2=second, etc.)
    """
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)
    
    matches = []
    
    # First pass: find clickable elements with matching text
    for node in root.iter():
        attrs = _get_node_attrs(node)
        if (text in attrs["text"] or text in attrs["content-desc"]) and attrs["clickable"]:
            bounds = _parse_bounds_str(attrs["bounds"])
            if bounds:
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                matches.append((cx, cy, True))
    
    # Second pass: non-clickable elements
    for node in root.iter():
        attrs = _get_node_attrs(node)
        if (text in attrs["text"] or text in attrs["content-desc"]) and not attrs["clickable"]:
            bounds = _parse_bounds_str(attrs["bounds"])
            if bounds:
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                matches.append((cx, cy, False))
    
    if not matches:
        return None, 0
    
    if index < 1 or index > len(matches):
        return None, len(matches)
    
    m = matches[index - 1]
    return (m[0], m[1]), len(matches)


def _find_element_by_id(device, resource_id):
    """Find element center by resource-id."""
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)
    for node in root.iter():
        attrs = _get_node_attrs(node)
        if resource_id in attrs["resource-id"]:
            bounds = _parse_bounds_str(attrs["bounds"])
            if bounds:
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return cx, cy
    return None


def _find_element_by_desc(device, desc):
    """Find element center by content-desc."""
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)
    for node in root.iter():
        attrs = _get_node_attrs(node)
        if desc in attrs["content-desc"]:
            bounds = _parse_bounds_str(attrs["bounds"])
            if bounds:
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return cx, cy
    return None


def _get_nth_interactive(device, n):
    """Get the Nth interactive element (1-indexed)."""
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)
    nodes = _collect_interactive_nodes(root)
    if 1 <= n <= len(nodes):
        attrs = nodes[n - 1]
        bounds = _parse_bounds_str(attrs["bounds"])
        if bounds:
            cx = (bounds[0] + bounds[2]) // 2
            cy = (bounds[1] + bounds[3]) // 2
            return cx, cy
    return None


def _get_display_size(device):
    try:
        info = device.info or {}
        w = int(info.get("displayWidth") or 0)
        h = int(info.get("displayHeight") or 0)
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return cfg.get_screen_size()


def _parse_coord(value, axis_size):
    raw = str(value).strip()
    if not raw:
        error("Empty coordinate value")
    if raw.endswith("%"):
        pct = float(raw[:-1].strip())
        return int(round(axis_size * pct / 100.0))
    f = float(raw)
    if 0.0 <= f <= 1.0 and "." in raw:
        return int(round(axis_size * f))
    return int(round(f))


def _resolve_point(device, x_val, y_val):
    w, h = _get_display_size(device)
    try:
        x = _parse_coord(x_val, w)
        y = _parse_coord(y_val, h)
    except Exception:
        error(f"Invalid coordinate: ({x_val},{y_val})")
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    return x, y


def _auto_swipe_duration(x1, y1, x2, y2):
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist <= 80:
        return 0.45
    if dist <= 180:
        return 0.75
    if dist <= 320:
        return 1.0
    return 1.2


def cmd_tap(args):
    """Tap at coordinates."""
    device = get_device(getattr(args, "device", None))
    x, y = _resolve_point(device, args.x, args.y)
    device.click(x, y)
    audit_log(f"input tap {x} {y}")
    ok(f"Tapped ({x},{y})")


def cmd_tap_text(args):
    """Tap element by text content."""
    device = get_device(getattr(args, "device", None))
    text = args.text
    index = int(getattr(args, "index", 1) or 1)
    pos, total = _find_element_by_text(device, text, index=index)
    if not pos and total == 0:
        error(f'Element with text "{text}" not found')
    if not pos and total > 0:
        error(f'--index {index} out of range, found {total} matches for "{text}"')
    device.click(pos[0], pos[1])
    idx_info = f" (match {index}/{total})" if total > 1 else ""
    audit_log(f'input tap-text "{text}" --index {index} -> ({pos[0]},{pos[1]})')
    ok(f'Tapped "{text}" at ({pos[0]},{pos[1]}){idx_info}')


def cmd_tap_id(args):
    """Tap element by resource-id."""
    device = get_device(getattr(args, "device", None))
    rid = args.resource_id
    pos = _find_element_by_id(device, rid)
    if not pos:
        error(f'Element with id "{rid}" not found')
    device.click(pos[0], pos[1])
    audit_log(f'input tap-id "{rid}" -> ({pos[0]},{pos[1]})')
    ok(f'Tapped id:{rid} at ({pos[0]},{pos[1]})')


def cmd_tap_desc(args):
    """Tap element by content-desc."""
    device = get_device(getattr(args, "device", None))
    desc = args.desc
    pos = _find_element_by_desc(device, desc)
    if not pos:
        error(f'Element with desc "{desc}" not found')
    device.click(pos[0], pos[1])
    audit_log(f'input tap-desc "{desc}" -> ({pos[0]},{pos[1]})')
    ok(f'Tapped desc:"{desc}" at ({pos[0]},{pos[1]})')


def cmd_tap_nth(args):
    """Tap the Nth element from the last numbered dump.
    
    Uses cached node list from the most recent 'ui dump --numbered' to ensure
    tap-nth targets the SAME elements the user saw, even if filters were applied.
    Falls back to a fresh full dump only if no cache exists.
    """
    device = get_device(getattr(args, "device", None))
    n = int(args.n)
    
    # Try cached numbered nodes first (preserves --search and other filter context)
    pos = get_cached_numbered_node(n)
    if pos:
        device.click(pos[0], pos[1])
        audit_log(f'input tap-nth {n} -> ({pos[0]},{pos[1]}) [cached]')
        ok(f'Tapped #{n} at ({pos[0]},{pos[1]})')
        return
    
    # No cache — fall back to fresh dump (backward compat)
    cached_count = get_cached_numbered_count()
    if cached_count > 0:
        error(f'Element #{n} out of range. Last numbered dump had {cached_count} elements. Run "ui dump --numbered" to refresh.')
    
    pos = _get_nth_interactive(device, n)
    if not pos:
        error(f'Interactive element #{n} not found. Run "ui dump --numbered" first to see elements.')
    device.click(pos[0], pos[1])
    audit_log(f'input tap-nth {n} -> ({pos[0]},{pos[1]})')
    ok(f'Tapped #{n} at ({pos[0]},{pos[1]})')


def cmd_long_tap(args):
    """Long press at coordinates."""
    device = get_device(getattr(args, "device", None))
    x, y = _resolve_point(device, args.x, args.y)
    duration = float(getattr(args, "duration", 1.0))
    device.long_click(x, y, duration=duration)
    audit_log(f"input long-tap {x} {y} duration={duration}")
    ok(f"Long-tapped ({x},{y}) for {duration}s")


def cmd_double_tap(args):
    """Double tap at coordinates."""
    device = get_device(getattr(args, "device", None))
    x, y = _resolve_point(device, args.x, args.y)
    device.double_click(x, y)
    audit_log(f"input double-tap {x} {y}")
    ok(f"Double-tapped ({x},{y})")


def cmd_swipe(args):
    """Swipe from (x1,y1) to (x2,y2)."""
    device = get_device(getattr(args, "device", None))
    x1, y1 = _resolve_point(device, args.x1, args.y1)
    x2, y2 = _resolve_point(device, args.x2, args.y2)
    # Support both --duration and positional 5th arg (AI often passes duration as 5th arg)
    duration = getattr(args, "duration", None)
    if duration is None:
        dur_pos = getattr(args, "duration_pos", None)
        if dur_pos is not None:
            try:
                duration = float(dur_pos)
                # If value > 10, it's likely milliseconds — convert to seconds
                if duration > 10:
                    duration = duration / 1000.0
            except ValueError:
                duration = None
        else:
            duration = None
    if duration is None:
        duration = _auto_swipe_duration(x1, y1, x2, y2)
    if duration <= 0:
        error("Duration must be > 0")
    device.swipe(x1, y1, x2, y2, duration=duration)
    audit_log(f"input swipe {x1} {y1} {x2} {y2}")
    ok(f"Swiped ({x1},{y1})->({x2},{y2})")


def cmd_swipe_dir(args):
    """Swipe in a direction (up/down/left/right)."""
    device = get_device(getattr(args, "device", None))
    direction = args.direction
    distance = float(getattr(args, "distance", 0.5))
    w, h = cfg.get_screen_size()
    cx, cy = w // 2, h // 2
    dist_x = int(w * distance / 2)
    dist_y = int(h * distance / 2)

    swipe_map = {
        "up": (cx, cy + dist_y, cx, cy - dist_y),
        "down": (cx, cy - dist_y, cx, cy + dist_y),
        "left": (cx + dist_x, cy, cx - dist_x, cy),
        "right": (cx - dist_x, cy, cx + dist_x, cy),
    }
    if direction not in swipe_map:
        error(f"Invalid direction: {direction}. Use up/down/left/right")
    x1, y1, x2, y2 = swipe_map[direction]
    device.swipe(x1, y1, x2, y2, duration=0.5)
    audit_log(f"input swipe-dir {direction} distance={distance}")
    ok(f"Swiped {direction}")


def cmd_scroll_to(args):
    """Scroll until specified text appears."""
    device = get_device(getattr(args, "device", None))
    target_text = args.text
    max_scrolls = int(getattr(args, "max_scrolls", 10))
    w, h = cfg.get_screen_size()

    for i in range(max_scrolls):
        pos = _find_element_by_text(device, target_text)
        if pos:
            ok(f'Found "{target_text}" at ({pos[0]},{pos[1]}) after {i} scrolls')
            return
        # Scroll down
        device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
        time.sleep(0.3)

    error(f'Text "{target_text}" not found after {max_scrolls} scrolls')


def _ensure_adb_keyboard(device):
    """Auto-switch to u2-compatible IME (AdbKeyboard or FastInputIME) if not active.
    Returns original IME id if switched, or None if no switch needed.
    """
    from .ime import _get_current_ime, _set_ime, _handle_ime_switch_popup
    import time

    current = _get_current_ime(device)
    # Already using a u2-compatible IME
    if "AdbKeyboard" in current or "FastInputIME" in current:
        return None

    # Find which u2 IME is installed
    out = device.shell("ime list -s").output
    u2_ime = None
    for line in out.strip().split("\n"):
        line = line.strip()
        if "AdbKeyboard" in line or "FastInputIME" in line:
            u2_ime = line
            break

    if not u2_ime:
        # No u2 IME installed, fall back to adb broadcast method
        return None

    # Enable and switch
    device.shell(f"ime enable {u2_ime}")
    _set_ime(device, u2_ime)
    time.sleep(0.3)
    _handle_ime_switch_popup(device)
    time.sleep(0.15)

    # Verify switch succeeded
    new_ime = _get_current_ime(device)
    if "AdbKeyboard" not in new_ime and "FastInputIME" not in new_ime:
        # Switch may have failed due to popup, try once more
        _handle_ime_switch_popup(device, max_wait=2)
        time.sleep(0.3)
        _set_ime(device, u2_ime)
        time.sleep(0.3)

    return current


def _restore_ime(device, original_ime):
    """Restore original IME after text input."""
    if not original_ime:
        return
    from .ime import _set_ime, _handle_ime_switch_popup
    import time
    time.sleep(0.15)
    _set_ime(device, original_ime)
    _handle_ime_switch_popup(device)


def _is_ascii_only(text):
    """Check if text contains only ASCII characters (digits, letters, symbols)."""
    return all(ord(c) < 128 for c in text)


# Keycode mapping for common ASCII chars
_KEYCODE_MAP = {}
# digits 0-9
for _i in range(10):
    _KEYCODE_MAP[str(_i)] = 7 + _i
# letters a-z
for _i in range(26):
    _KEYCODE_MAP[chr(ord('a') + _i)] = 29 + _i
    _KEYCODE_MAP[chr(ord('A') + _i)] = 29 + _i  # same keycode, shift handled separately
# common symbols
_KEYCODE_MAP.update({
    ' ': 62, '.': 56, ',': 55, '@': 77, '#': 18, '*': 17,
    '-': 69, '_': 69, '+': 81, '=': 70, '(': 162, ')': 163,
    '/': 76, '\\': 73, ';': 74, "'": 75, '[': 71, ']': 72,
    '!': 0, '?': 0, ':': 0,  # these need shift or special handling
})


def _input_via_keyevent(device, text):
    """Input text character by character via keyevent. Best compat for RN/Flutter."""
    for ch in text:
        kc = _KEYCODE_MAP.get(ch)
        if kc and kc > 0:
            if ch.isupper():
                # SHIFT + keycode for uppercase
                device.shell(f"input keyevent --longpress 59 {kc}")
            else:
                device.shell(f"input keyevent {kc}")
        elif kc == 0:
            # Unsupported keyevent, fall back to input text for this char
            device.shell(f"input text '{ch}'")
        else:
            device.shell(f"input text '{ch}'")
        time.sleep(0.05)


def cmd_text(args):
    """Input text (supports Chinese via u2). Auto-switches IME if needed.
    
    Strategy:
    - Pure ASCII (numbers, English): keyevent per character (best RN/Flutter compat)
    - Contains Chinese/Unicode: send_keys via AdbKeyboard + clear/set to trigger InputConnection
    """
    device = get_device(getattr(args, "device", None))
    content = args.content

    if _is_ascii_only(content):
        # Pure ASCII: use keyevent for each character (triggers real key events)
        _input_via_keyevent(device, content)
    else:
        # Contains Chinese/Unicode: must use AdbKeyboard send_keys
        _ensure_adb_keyboard(device)
        device.send_keys(content)
        # Trigger InputConnection so RN/Flutter frameworks detect the change
        try:
            focused = device(focused=True)
            if focused.exists:
                cur = focused.get_text() or ""
                if cur:
                    focused.clear_text()
                    time.sleep(0.05)
                    focused.set_text(cur)
        except Exception:
            pass

    audit_log(f'input text "{content[:30]}..."' if len(content) > 30 else f'input text "{content}"')
    ok(f"Typed text ({len(content)} chars)")


def cmd_set_text(args):
    """Set text on a specific input field. Auto-switches IME if needed.
    
    Selector matching strategy (in order):
    1. textContains (fuzzy text match — handles trailing spaces, commas, etc.)
    2. resourceId (exact match)
    3. description (content-desc match)
    4. If selector looks like it targets an input field, try className='EditText'
    5. focused=True as last resort
    """
    device = get_device(getattr(args, "device", None))
    selector = args.selector
    content = args.content

    _ensure_adb_keyboard(device)

    el = None
    if selector:
        # Strip trailing punctuation/spaces for fuzzy matching
        clean_sel = selector.rstrip(" ,，.。、")
        
        # Try textContains first (handles "搜索," matching "搜索, " etc.)
        if clean_sel:
            el = device(textContains=clean_sel)
        if not el or not el.exists:
            el = device(text=selector)
        if not el or not el.exists:
            el = device(resourceId=selector)
        if not el or not el.exists:
            el = device(description=selector)
        if not el or not el.exists:
            # Try finding any EditText with matching text
            if clean_sel:
                el = device(className="android.widget.EditText", textContains=clean_sel)
        if not el or not el.exists:
            # Last resort: any focused EditText
            el = device(className="android.widget.EditText", focused=True)
    else:
        el = device(focused=True)

    if el and el.exists:
        el.set_text(content)
        audit_log(f'input set-text "{selector}" "{content[:30]}"')
        ok(f'Set text on "{selector}"')
    else:
        error(f'Input field "{selector}" not found')


def cmd_clear(args):
    """Clear text from input field."""
    device = get_device(getattr(args, "device", None))
    selector = getattr(args, "selector", None)

    if selector:
        clean_sel = selector.rstrip(" ,，.。、")
        el = None
        if clean_sel:
            el = device(textContains=clean_sel)
        if not el or not el.exists:
            el = device(text=selector)
        if not el or not el.exists:
            el = device(resourceId=selector)
        if el and el.exists:
            el.clear_text()
            ok(f'Cleared "{selector}"')
        else:
            error(f'Input field "{selector}" not found')
    else:
        el = device(focused=True)
        if el.exists:
            el.clear_text()
            ok("Cleared focused input")
        else:
            error("No focused input field found")
    audit_log(f"input clear {selector or 'focused'}")


def cmd_key(args):
    """Send a key event."""
    device = get_device(getattr(args, "device", None))
    keycode = args.keycode.upper()

    key_map = {
        "BACK": "back",
        "HOME": "home",
        "ENTER": "enter",
        "VOLUME_UP": "volume_up",
        "VOLUME_DOWN": "volume_down",
        "POWER": "power",
        "MENU": "menu",
        "RECENT_APPS": "recent",
        "CAMERA": "camera",
        "SEARCH": "search",
        "DELETE": "delete",
        "TAB": "tab",
        "SPACE": "space",
    }

    if keycode in key_map:
        device.press(key_map[keycode])
    else:
        # Try as numeric keycode
        try:
            device.press(int(keycode))
        except ValueError:
            # Try as raw keyevent via shell
            device.shell(f"input keyevent {keycode}")
    audit_log(f"input key {keycode}")
    ok(f"Key: {keycode}")


def cmd_pinch(args):
    """Pinch in/out gesture."""
    device = get_device(getattr(args, "device", None))
    direction = args.direction  # "in" or "out"
    scale = float(getattr(args, "scale", 0.5))

    if direction == "in":
        device.pinch_in(percent=int(scale * 100))
    elif direction == "out":
        device.pinch_out(percent=int(scale * 100))
    else:
        error("Direction must be 'in' or 'out'")
    audit_log(f"input pinch {direction} scale={scale}")
    ok(f"Pinch {direction}")


def cmd_drag(args):
    """Drag from one point to another."""
    device = get_device(getattr(args, "device", None))
    x1, y1 = _resolve_point(device, args.x1, args.y1)
    x2, y2 = _resolve_point(device, args.x2, args.y2)
    duration = getattr(args, "duration", None)
    if duration is None:
        duration = _auto_swipe_duration(x1, y1, x2, y2)
    else:
        duration = float(duration)
    if duration <= 0:
        error("Duration must be > 0")
    device.drag(x1, y1, x2, y2, duration=duration)
    audit_log(f"input drag {x1} {y1} {x2} {y2}")
    ok(f"Dragged ({x1},{y1})->({x2},{y2})")


def cmd_multi_tap(args):
    """Multi-point tap (placeholder - u2 limited support)."""
    device = get_device(getattr(args, "device", None))
    points_str = args.points  # "x1,y1 x2,y2 ..."
    points = []
    for p in points_str:
        parts = p.split(",")
        if len(parts) == 2:
            points.append(_resolve_point(device, parts[0], parts[1]))

    # Tap each point sequentially (true multi-touch limited in u2)
    for x, y in points:
        device.click(x, y)
        time.sleep(0.03)
    audit_log(f"input multi-tap {points}")
    ok(f"Multi-tapped {len(points)} points")


def cmd_gesture(args):
    """Custom gesture path for pattern unlock etc."""
    device = get_device(getattr(args, "device", None))
    coords_str = args.coords  # "x1,y1 x2,y2 x3,y3 ..."
    points = []
    for c in coords_str:
        parts = c.split(",")
        if len(parts) == 2:
            points.append(_resolve_point(device, parts[0], parts[1]))

    if len(points) < 2:
        error("Need at least 2 points for gesture")

    # Use swipe_points for gesture
    duration = float(getattr(args, "duration", 0.5))
    device.swipe_points(points, duration=duration)
    audit_log(f"input gesture {len(points)} points")
    ok(f"Gesture through {len(points)} points")


# ─── CAPTCHA SWIPE ─────────────────────────────────────────────────────────────

def _easing_linear(t):
    return t

def _easing_ease_in(t):
    return t * t

def _easing_ease_out(t):
    return 1.0 - (1.0 - t) * (1.0 - t)

def _easing_ease_in_out(t):
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0

def _easing_human(t):
    """Ease-in-out with slight randomness to mimic human finger movement."""
    base = _easing_ease_in_out(t)
    noise_amp = 0.015 * math.sin(math.pi * t)
    noise = random.uniform(-noise_amp, noise_amp)
    return max(0.0, min(1.0, base + noise))

_EASING_FUNCS = {
    "linear": _easing_linear,
    "ease-in": _easing_ease_in,
    "ease-out": _easing_ease_out,
    "ease-in-out": _easing_ease_in_out,
    "human": _easing_human,
}


def _generate_captcha_path(x1, y1, x2, y2, easing="human", overshoot=0,
                           y_wobble=0, steps=30, hold_start=0.12,
                           hold_end=0.08, duration=0.8):
    """Generate a human-like swipe path for CAPTCHA slider.

    Returns (points, total_duration) where points is a list of (x, y) tuples
    and total_duration includes hold times.

    The trick: swipe_points distributes time evenly across all point-to-point
    segments. By repeating points at start/end we create natural hold pauses.
    By spacing movement points according to easing, we control speed profile.
    """
    easing_fn = _EASING_FUNCS.get(easing, _easing_human)

    total_time = hold_start + duration + hold_end
    if total_time <= 0:
        total_time = 1.0

    # Calculate how many points to allocate per phase (proportional to time)
    total_pts = steps + 10  # base pool
    hold_start_pts = max(2, int(round(total_pts * hold_start / total_time)))
    hold_end_pts = max(2, int(round(total_pts * hold_end / total_time)))
    move_pts = max(10, total_pts - hold_start_pts - hold_end_pts)

    points = []

    # Phase 1: Hold at start (finger down, slight jitter to avoid dedup)
    for i in range(hold_start_pts):
        jx = x1 + random.randint(-1, 1)
        jy = y1 + random.randint(-1, 1)
        points.append((jx, jy))

    # Phase 2: Movement with easing + y-wobble
    dx = x2 - x1
    dy = y2 - y1
    for i in range(move_pts + 1):
        t = i / move_pts
        progress = easing_fn(t)

        x = x1 + dx * progress
        y = y1 + dy * progress

        # Y-wobble: sinusoidal envelope, max in middle, zero at edges
        if y_wobble > 0 and 0 < t < 1:
            envelope = math.sin(math.pi * t)
            wobble = random.uniform(-y_wobble, y_wobble) * envelope
            y += wobble

        points.append((int(round(x)), int(round(y))))

    # Phase 3: Overshoot past target then settle back
    if overshoot > 0:
        os_steps = max(4, move_pts // 5)
        # Overshoot: ease-out to overshoot position
        for i in range(1, os_steps + 1):
            t = i / os_steps
            ox = x2 + overshoot * _easing_ease_out(t)
            oy = y2 + random.randint(-1, 1)
            points.append((int(round(ox)), oy))
        # Settle back: ease-in back to target
        for i in range(1, os_steps + 1):
            t = i / os_steps
            ox = x2 + overshoot * (1.0 - _easing_ease_in(t))
            oy = y2 + random.randint(-1, 1)
            points.append((int(round(ox)), oy))
        # Adjust total duration to account for overshoot movement time
        overshoot_time = duration * 0.25
        total_time += overshoot_time

    # Phase 4: Hold at end (finger still before release)
    for i in range(hold_end_pts):
        jx = x2 + random.randint(-1, 1)
        jy = y2 + random.randint(-1, 1)
        points.append((jx, jy))

    return points, total_time


def _verify_captcha_result(device, wait_after=1.5):
    """Check UI after captcha swipe to determine pass/fail.

    Returns dict: {"passed": bool, "detail": str}
    """
    time.sleep(wait_after)

    success_keywords = ["验证成功", "通过验证", "验证通过", "操作成功", "滑动成功"]
    failure_keywords = ["验证失败", "请重试", "再试一次", "拖动滑块", "请通过以下验证",
                        "向右拖动", "滑动验证", "请按住滑块"]

    try:
        xml_str = _get_ui_xml(device)
        root = _parse_xml(xml_str)
        all_text = []
        for node in root.iter():
            attrs = _get_node_attrs(node)
            t = attrs.get("text", "").strip()
            d = attrs.get("content-desc", "").strip()
            if t:
                all_text.append(t)
            if d:
                all_text.append(d)

        combined = " ".join(all_text)

        for kw in success_keywords:
            if kw in combined:
                return {"passed": True, "detail": f'Found success indicator: "{kw}"'}

        for kw in failure_keywords:
            if kw in combined:
                return {"passed": False, "detail": f'Found failure indicator: "{kw}" — captcha gap likely refreshed to new position, re-screenshot before retry'}

        # No clear indicator — might have navigated away (success) or still loading
        return {"passed": None, "detail": "No clear success/failure indicator found. Take a screenshot to visually confirm."}

    except Exception as e:
        return {"passed": None, "detail": f"Verification check failed: {e}. Take a screenshot to confirm."}


def cmd_captcha_swipe(args):
    """Human-like swipe for CAPTCHA slider verification.

    AI controls all parameters to maximize chance of passing:
    - Coordinates: slider start and target end
    - Duration: movement time (affects perceived speed)
    - Easing: speed curve (human = natural acceleration/deceleration + noise)
    - Hold times: press-and-hold before/after movement
    - Overshoot: slide past target then settle back (mimics human inertia)
    - Y-wobble: natural vertical deviation during horizontal drag
    - Steps: path resolution (more = smoother trajectory)
    """
    device = get_device(getattr(args, "device", None))
    x1, y1 = _resolve_point(device, args.x1, args.y1)
    x2, y2 = _resolve_point(device, args.x2, args.y2)

    duration = float(getattr(args, "duration", None) or 0.8)
    hold_start = float(getattr(args, "hold_start", None) or 0.12)
    hold_end = float(getattr(args, "hold_end", None) or 0.08)
    easing = getattr(args, "easing", None) or "human"
    overshoot = int(getattr(args, "overshoot", None) or 0)
    y_wobble = int(getattr(args, "y_wobble", None) or 0)
    steps = int(getattr(args, "steps", None) or 30)
    do_verify = getattr(args, "verify", False)
    wait_after = float(getattr(args, "wait_after", None) or 1.5)

    if easing not in _EASING_FUNCS:
        error(f"Unknown easing: {easing}. Choose from: {', '.join(_EASING_FUNCS.keys())}")

    if duration <= 0:
        error("Duration must be > 0")
    if steps < 5:
        error("Steps must be >= 5")

    # Generate the human-like path
    points, total_duration = _generate_captcha_path(
        x1, y1, x2, y2,
        easing=easing,
        overshoot=overshoot,
        y_wobble=y_wobble,
        steps=steps,
        hold_start=hold_start,
        hold_end=hold_end,
        duration=duration,
    )

    # Execute the swipe
    device.swipe_points(points, duration=total_duration)

    params_str = (f"easing={easing} duration={duration:.2f}s "
                  f"hold={hold_start:.2f}+{hold_end:.2f}s "
                  f"overshoot={overshoot}px y_wobble={y_wobble}px "
                  f"steps={steps} points={len(points)}")
    audit_log(f"input captcha-swipe ({x1},{y1})->({x2},{y2}) {params_str}")

    result_lines = [
        f"Captcha-swiped ({x1},{y1})->({x2},{y2})",
        f"  Path: {len(points)} points, {total_duration:.2f}s total",
        f"  Params: {params_str}",
    ]

    # Verify if requested
    if do_verify:
        vr = _verify_captcha_result(device, wait_after=wait_after)
        if vr["passed"] is True:
            result_lines.append(f"  ✅ Verification: PASSED — {vr['detail']}")
        else:
            if vr["passed"] is False:
                result_lines.append(f"  ❌ Verification: FAILED — {vr['detail']}")
            else:
                result_lines.append(f"  ⚠️ Verification: UNCERTAIN — {vr['detail']}")
            # Auto-screenshot on failure/uncertain so user sees current state
            try:
                import os, datetime as _dt
                _media_dir = os.path.expanduser("~/.openclaw/media/phone")
                os.makedirs(_media_dir, exist_ok=True)
                _ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                _ss_path = os.path.join(_media_dir, f"captcha_fail_{_ts}.png")
                device.screenshot().save(_ss_path)
                print(f"MEDIA:{_ss_path}")
                result_lines.append(f"  📸 Auto-screenshot sent to user: {_ss_path}")
            except Exception:
                result_lines.append("  📸 Auto-screenshot failed, AI should run ./phone screenshot manually")

    ok("\n".join(result_lines))
