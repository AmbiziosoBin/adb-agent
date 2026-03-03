"""Advanced automation: wait, assert, shell, intent, watcher, clipboard, macros, batch."""

import os
import re
import time
import json
import datetime

from .connection import get_device, adb_shell
from .utils import output, error, ok, audit_log, mark_output_handled
from .ui import _get_ui_xml, _parse_xml, _get_node_attrs
from . import config as cfg

# Macro storage directory
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MACRO_DIR = os.path.join(_SKILL_ROOT, "macros")


def _find_element_by_text(device, text):
    """Check if text exists in UI."""
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)
    for node in root.iter():
        attrs = _get_node_attrs(node)
        if text in attrs["text"] or text in attrs["content-desc"]:
            return True
    return False


def cmd_wait_text(args):
    """Wait for text to appear on screen."""
    device = get_device(getattr(args, "device", None))
    text = args.text
    timeout = float(getattr(args, "timeout", 10))
    interval = 0.5
    elapsed = 0

    while elapsed < timeout:
        if _find_element_by_text(device, text):
            ok(f'Text "{text}" appeared after {elapsed:.0f}s')
            audit_log(f'wait text "{text}" -> found')
            return
        time.sleep(interval)
        elapsed += interval

    error(f'Text "{text}" did not appear within {timeout}s')


def cmd_wait_gone(args):
    """Wait for text to disappear from screen."""
    device = get_device(getattr(args, "device", None))
    text = args.text
    timeout = float(getattr(args, "timeout", 10))
    interval = 0.5
    elapsed = 0

    while elapsed < timeout:
        if not _find_element_by_text(device, text):
            ok(f'Text "{text}" gone after {elapsed:.0f}s')
            audit_log(f'wait gone "{text}" -> gone')
            return
        time.sleep(interval)
        elapsed += interval

    error(f'Text "{text}" still present after {timeout}s')


def cmd_wait_activity(args):
    """Wait for specific Activity to appear."""
    device = get_device(getattr(args, "device", None))
    activity = args.activity
    timeout = float(getattr(args, "timeout", 10))
    interval = 0.5
    elapsed = 0

    while elapsed < timeout:
        current = device.app_current()
        if activity in current.get("activity", ""):
            ok(f'Activity "{activity}" appeared after {elapsed:.0f}s')
            audit_log(f'wait activity "{activity}" -> found')
            return
        time.sleep(interval)
        elapsed += interval

    error(f'Activity "{activity}" did not appear within {timeout}s')


def cmd_assert_text(args):
    """Assert text exists on screen."""
    device = get_device(getattr(args, "device", None))
    text = args.text

    if _find_element_by_text(device, text):
        ok(f'PASS: text "{text}" exists')
    else:
        error(f'FAIL: text "{text}" not found')
    audit_log(f'assert text "{text}"')


def cmd_assert_not_text(args):
    """Assert text does NOT exist on screen."""
    device = get_device(getattr(args, "device", None))
    text = args.text

    if not _find_element_by_text(device, text):
        ok(f'PASS: text "{text}" not present')
    else:
        error(f'FAIL: text "{text}" unexpectedly found')
    audit_log(f'assert not-text "{text}"')


def cmd_shell(args):
    """Execute arbitrary adb shell command."""
    device = get_device(getattr(args, "device", None))
    command = args.command
    result = device.shell(command)
    out = result.output if hasattr(result, 'output') else str(result)
    output(out.strip())
    audit_log(f"shell {command[:50]}")


def cmd_intent(args):
    """Send an Android Intent."""
    device = get_device(getattr(args, "device", None))
    action = args.action
    data = getattr(args, "data", None)
    package = getattr(args, "package", None)
    extras = getattr(args, "extra", None)

    cmd = f"am start -a {action}"
    if data:
        cmd += f" -d {data}"
    if package:
        cmd += f" -n {package}"
    if extras:
        for extra in extras:
            if "=" in extra:
                key, val = extra.split("=", 1)
                cmd += f" --es {key} {val}"

    result = device.shell(cmd)
    output(result.output.strip() if hasattr(result, 'output') else str(result))
    audit_log(f"intent {action}")
    ok(f"Intent sent: {action}")


def cmd_clipboard_get(args):
    """Get clipboard content."""
    device = get_device(getattr(args, "device", None))
    # u2 approach
    try:
        clip = device.clipboard
        output(clip if clip else "(clipboard empty)")
    except Exception:
        out = device.shell("am broadcast -a clipper.get").output
        output(out.strip() or "(clipboard empty or not accessible)")
    audit_log("clipboard get")


def cmd_clipboard_set(args):
    """Set clipboard content."""
    device = get_device(getattr(args, "device", None))
    content = args.content
    try:
        device.set_clipboard(content)
        ok(f"Clipboard set ({len(content)} chars)")
    except Exception:
        device.shell(f'am broadcast -a clipper.set -e text "{content}"')
        ok(f"Clipboard set via broadcast ({len(content)} chars)")
    audit_log(f'clipboard set "{content[:20]}"')


def cmd_open_url(args):
    """Open URL in default browser."""
    device = get_device(getattr(args, "device", None))
    url = args.url
    device.shell(f"am start -a android.intent.action.VIEW -d {url}")
    audit_log(f"open-url {url}")
    ok(f"Opening {url}")


def cmd_open_settings(args):
    """Open system settings."""
    device = get_device(getattr(args, "device", None))
    page = getattr(args, "page", None)

    settings_map = {
        None: "android.settings.SETTINGS",
        "wifi": "android.settings.WIFI_SETTINGS",
        "bluetooth": "android.settings.BLUETOOTH_SETTINGS",
        "display": "android.settings.DISPLAY_SETTINGS",
        "sound": "android.settings.SOUND_SETTINGS",
        "battery": "android.intent.action.POWER_USAGE_SUMMARY",
        "storage": "android.settings.INTERNAL_STORAGE_SETTINGS",
        "apps": "android.settings.APPLICATION_SETTINGS",
        "location": "android.settings.LOCATION_SOURCE_SETTINGS",
        "security": "android.settings.SECURITY_SETTINGS",
        "developer": "android.settings.APPLICATION_DEVELOPMENT_SETTINGS",
        "date": "android.settings.DATE_SETTINGS",
        "accessibility": "android.settings.ACCESSIBILITY_SETTINGS",
        "language": "android.settings.LOCALE_SETTINGS",
        "about": "android.settings.DEVICE_INFO_SETTINGS",
        "network": "android.settings.WIRELESS_SETTINGS",
        "airplane": "android.settings.AIRPLANE_MODE_SETTINGS",
        "nfc": "android.settings.NFC_SETTINGS",
        "notification": "android.settings.NOTIFICATION_SETTINGS",
    }

    action = settings_map.get(page, f"android.settings.{page.upper()}_SETTINGS" if page else "android.settings.SETTINGS")
    device.shell(f"am start -a {action}")
    audit_log(f"open-settings {page or 'main'}")
    ok(f"Opened settings: {page or 'main'}")


def cmd_watcher_add(args):
    """Add UI watcher for auto-handling popups."""
    device = get_device(getattr(args, "device", None))
    name = args.name
    when_type = args.when_type  # text or id
    when_value = args.when_value
    do_action = args.do_action  # click, back, dismiss

    if when_type == "text":
        if do_action == "click":
            device.watcher(name).when(text=when_value).click(text=when_value)
        elif do_action == "back":
            device.watcher(name).when(text=when_value).press("back")
        else:
            device.watcher(name).when(text=when_value).click(text=when_value)
    elif when_type == "id":
        if do_action == "click":
            device.watcher(name).when(resourceId=when_value).click(resourceId=when_value)
        elif do_action == "back":
            device.watcher(name).when(resourceId=when_value).press("back")

    device.watcher.start()
    audit_log(f"watcher add {name} when={when_type}:{when_value} do={do_action}")
    ok(f"Watcher '{name}' added")


def cmd_watcher_remove(args):
    """Remove UI watcher."""
    device = get_device(getattr(args, "device", None))
    name = getattr(args, "name", None)
    remove_all = getattr(args, "all", False)

    if remove_all:
        device.watcher.remove()
        ok("All watchers removed")
    elif name:
        device.watcher.remove(name)
        ok(f"Watcher '{name}' removed")
    else:
        error("Specify watcher name or --all")
    audit_log(f"watcher remove {name or '--all'}")


def cmd_watcher_list(args):
    """List active watchers."""
    device = get_device(getattr(args, "device", None))
    watchers = device.watcher.running()
    if watchers:
        output(f"Active watchers: {watchers}")
    else:
        output("(no active watchers)")
    audit_log("watcher list")


def cmd_toast(args):
    """Get recent toast messages."""
    device = get_device(getattr(args, "device", None))
    try:
        toast = device.toast.get_message(wait_timeout=3)
        if toast:
            output(f"Toast: {toast}")
        else:
            output("(no recent toast)")
    except Exception:
        output("(toast capture not available)")
    audit_log("toast")


def cmd_location_mock(args):
    """Mock GPS location."""
    device = get_device(getattr(args, "device", None))
    lat = args.latitude
    lon = args.longitude

    # Enable mock locations
    device.shell("settings put secure mock_location 1")
    # Use appops or similar
    device.shell(f"am start -a android.intent.action.VIEW -d geo:{lat},{lon}")
    audit_log(f"location mock {lat},{lon}")
    ok(f"Location mock set to {lat},{lon}")
    output("Note: App-level mock location provider may be needed for full GPS spoofing")


def cmd_location_mock_stop(args):
    """Stop location mocking."""
    device = get_device(getattr(args, "device", None))
    device.shell("settings put secure mock_location 0")
    audit_log("location mock-stop")
    ok("Location mock stopped")


def cmd_batch(args):
    """Execute batch commands from file."""
    device = get_device(getattr(args, "device", None))
    batch_file = args.file

    if not os.path.exists(batch_file):
        error(f"Batch file not found: {batch_file}")

    with open(batch_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    count = 0
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        output(f"[{i}] {line}")
        # Execute as shell command through the tool
        result = device.shell(line)
        out = result.output if hasattr(result, 'output') else str(result)
        if out.strip():
            output(f"  → {out.strip()[:200]}")
        count += 1
        time.sleep(0.1)

    audit_log(f"batch {batch_file} ({count} commands)")
    ok(f"Batch complete: {count} commands executed")


def cmd_sleep(args):
    """Wait for specified seconds."""
    seconds = float(args.seconds)
    time.sleep(seconds)
    ok(f"Waited {seconds}s")
    audit_log(f"sleep {seconds}")


def cmd_macro_record(args):
    """Create a macro template file for batch execution.
    Note: This creates a template file for you to fill in with commands (one per line).
    It does NOT live-record your interactions. Use 'macro play' to execute the file.
    """
    name = args.name
    os.makedirs(_MACRO_DIR, exist_ok=True)
    macro_path = os.path.join(_MACRO_DIR, f"{name}.txt")

    # Create template macro file
    with open(macro_path, "w", encoding="utf-8") as f:
        f.write(f"# Macro: {name}\n")
        f.write(f"# Created: {datetime.datetime.now().isoformat()}\n")
        f.write("# Add adb shell commands below, one per line.\n")
        f.write("# Lines starting with # are comments.\n")
        f.write("# Example:\n")
        f.write("#   input tap 540 1200\n")
        f.write("#   sleep 1\n")
        f.write("#   am start -n com.tencent.mm/.ui.LauncherUI\n\n")

    audit_log(f"macro record {name}")
    ok(f"Macro template created: {macro_path}")
    output("Edit the file to add commands, then run 'macro play' to execute")


def cmd_macro_play(args):
    """Play back a recorded macro."""
    name = args.name
    macro_path = os.path.join(_MACRO_DIR, f"{name}.txt")

    if not os.path.exists(macro_path):
        error(f"Macro '{name}' not found")

    # Reuse batch execution
    args.file = macro_path
    cmd_batch(args)
    audit_log(f"macro play {name}")


def cmd_macro_list(args):
    """List saved macros."""
    if not os.path.exists(_MACRO_DIR):
        output("(no macros)")
        return

    macros = [f.replace(".txt", "") for f in os.listdir(_MACRO_DIR) if f.endswith(".txt")]
    if macros:
        for m in sorted(macros):
            output(f"  {m}")
        output(f"\n[Total: {len(macros)}]")
    else:
        output("(no macros)")
    audit_log("macro list")


def cmd_macro_delete(args):
    """Delete a saved macro."""
    name = args.name
    macro_path = os.path.join(_MACRO_DIR, f"{name}.txt")

    if not os.path.exists(macro_path):
        error(f"Macro '{name}' not found")

    os.remove(macro_path)
    audit_log(f"macro delete {name}")
    ok(f"Macro '{name}' deleted")


def cmd_batch_steps(args):
    """Execute multiple steps in one call. Accepts JSON input from AI.
    
    JSON format (array of steps):
    [
      {"action": "input", "command": "tap-text", "args": {"text": "同意"}},
      {"action": "input", "command": "text", "args": {"content": "13800138000"}},
      {"action": "wait", "command": "text", "args": {"text": "验证码", "timeout": 5}},
      {"action": "input", "command": "key", "args": {"keycode": "ENTER"}}
    ]
    
    Each step has:
      - action: command category (input, ui, app, wait, device, shell, sleep)
      - command: subcommand name (tap-text, text, key, launch, dump, etc.)
      - args: dict of arguments for the subcommand
      - verify_text (optional): text to verify exists after this step
      - description (optional): human-readable step description
    """
    from .utils import start_command_timer, _elapsed_ms, is_json_mode, set_json_mode, _ts
    import json as _json
    import sys
    import traceback

    steps_input = args.steps_json
    stop_on_error = not getattr(args, "no_stop_on_error", False)
    delay_between = float(getattr(args, "delay", 0.3))
    verify_all = getattr(args, "verify", False)

    # Parse JSON — from string or file
    try:
        if os.path.isfile(steps_input):
            with open(steps_input, "r", encoding="utf-8") as f:
                steps = _json.load(f)
        else:
            steps = _json.loads(steps_input)
    except (_json.JSONDecodeError, Exception) as e:
        error(f"Invalid JSON input: {e}",
              hint="Provide a JSON array of steps, e.g.: [{\"action\":\"input\",\"command\":\"tap-text\",\"args\":{\"text\":\"确定\"}}]",
              cause=str(e))
        return

    if not isinstance(steps, list) or len(steps) == 0:
        error("steps_json must be a non-empty JSON array",
              hint="Example: [{\"action\":\"input\",\"command\":\"tap-text\",\"args\":{\"text\":\"确定\"}}]")
        return

    device = get_device(getattr(args, "device", None))
    total = len(steps)
    results = []
    completed = 0
    failed = 0
    batch_start = time.time()

    # Force JSON mode for batch-steps output
    was_json = is_json_mode()
    set_json_mode(True)

    for idx, step in enumerate(steps, 1):
        step_start = time.time()
        step_action = step.get("action", "")
        step_cmd = step.get("command", "")
        step_args = step.get("args", {})
        step_desc = step.get("description", f"{step_action} {step_cmd}")
        verify_text = step.get("verify_text", None)

        step_result = {
            "step": idx,
            "description": step_desc,
            "action": step_action,
            "command": step_cmd,
            "status": "ok",
            "duration_ms": 0,
            "result": "",
        }

        try:
            _execute_single_step(device, step_action, step_cmd, step_args)
            step_result["result"] = f"Step {idx} completed: {step_desc}"
            completed += 1

            # Post-step verification
            if verify_text or verify_all:
                time.sleep(0.2)
                vtext = verify_text
                if vtext:
                    found = _find_element_by_text(device, vtext)
                    if not found:
                        step_result["status"] = "warn"
                        step_result["result"] += f" | verify_text '{vtext}' not found"

        except SystemExit:
            step_result["status"] = "error"
            step_result["result"] = f"Step {idx} failed: {step_desc}"
            failed += 1
            if stop_on_error:
                step_result["duration_ms"] = int((time.time() - step_start) * 1000)
                results.append(step_result)
                break
        except Exception as e:
            step_result["status"] = "error"
            step_result["result"] = f"Step {idx} error: {str(e)}"
            step_result["error"] = str(e)
            failed += 1
            if stop_on_error:
                step_result["duration_ms"] = int((time.time() - step_start) * 1000)
                results.append(step_result)
                break

        step_result["duration_ms"] = int((time.time() - step_start) * 1000)
        results.append(step_result)

        # Delay between steps (skip after last)
        if idx < total:
            time.sleep(delay_between)

    batch_duration = int((time.time() - batch_start) * 1000)

    # Output final batch result as JSON
    batch_result = {
        "status": "ok" if failed == 0 else "partial" if completed > 0 else "error",
        "command": "batch-steps",
        "timestamp": datetime.datetime.now().isoformat(),
        "duration_ms": batch_duration,
        "total_steps": total,
        "completed": completed,
        "failed": failed,
        "steps": results,
    }

    # Reset JSON mode and print the result directly
    set_json_mode(was_json)
    print(_json.dumps(batch_result, ensure_ascii=False))
    audit_log(f"batch-steps total={total} completed={completed} failed={failed} duration={batch_duration}ms")
    mark_output_handled()


def _execute_single_step(device, action, command, step_args):
    """Execute a single batch step by dispatching to the appropriate handler.
    
    This avoids subprocess overhead by calling handlers directly in-process.
    """
    from .ui import _get_ui_xml, _parse_xml, _get_node_attrs, _parse_bounds_str, _collect_interactive_nodes, _save_numbered_cache
    from .input_ctrl import (
        _find_element_by_text, _find_element_by_id, _find_element_by_desc,
        _ensure_adb_keyboard, _input_via_keyevent, _is_ascii_only
    )
    from . import config as cfg_mod

    if action == "input":
        if command == "tap-text":
            text = step_args.get("text", "")
            index = int(step_args.get("index", 1))
            pos, total = _find_element_by_text(device, text, index=index)
            if not pos:
                raise RuntimeError(f'Element with text "{text}" not found')
            device.click(pos[0], pos[1])

        elif command == "tap":
            x, y = int(step_args["x"]), int(step_args["y"])
            device.click(x, y)

        elif command == "tap-id":
            rid = step_args.get("resource_id", "")
            pos = _find_element_by_id(device, rid)
            if not pos:
                raise RuntimeError(f'Element with id "{rid}" not found')
            device.click(pos[0], pos[1])

        elif command == "tap-desc":
            desc = step_args.get("desc", "")
            pos = _find_element_by_desc(device, desc)
            if not pos:
                raise RuntimeError(f'Element with desc "{desc}" not found')
            device.click(pos[0], pos[1])

        elif command == "tap-nth":
            from .ui import get_cached_numbered_node
            n = int(step_args.get("n", 1))
            pos = get_cached_numbered_node(n)
            if not pos:
                raise RuntimeError(f'Element #{n} not found in cache. Run ui dump --numbered first.')
            device.click(pos[0], pos[1])

        elif command == "text":
            content = step_args.get("content", "")
            if _is_ascii_only(content):
                _input_via_keyevent(device, content)
            else:
                _ensure_adb_keyboard(device)
                device.send_keys(content)

        elif command == "set-text":
            selector = step_args.get("selector", "")
            content = step_args.get("content", "")
            _ensure_adb_keyboard(device)
            el = device(textContains=selector) if selector else device(focused=True)
            if el and el.exists:
                el.set_text(content)
            else:
                raise RuntimeError(f'Input field "{selector}" not found')

        elif command == "key":
            keycode = step_args.get("keycode", "").upper()
            key_map = {
                "BACK": "back", "HOME": "home", "ENTER": "enter",
                "VOLUME_UP": "volume_up", "VOLUME_DOWN": "volume_down",
                "POWER": "power", "MENU": "menu", "DELETE": "delete",
            }
            if keycode in key_map:
                device.press(key_map[keycode])
            else:
                device.shell(f"input keyevent {keycode}")

        elif command == "swipe-dir":
            direction = step_args.get("direction", "down")
            distance = float(step_args.get("distance", 0.5))
            w, h = cfg_mod.get_screen_size()
            cx, cy = w // 2, h // 2
            dist_x, dist_y = int(w * distance / 2), int(h * distance / 2)
            swipe_map = {
                "up": (cx, cy + dist_y, cx, cy - dist_y),
                "down": (cx, cy - dist_y, cx, cy + dist_y),
                "left": (cx + dist_x, cy, cx - dist_x, cy),
                "right": (cx - dist_x, cy, cx + dist_x, cy),
            }
            x1, y1, x2, y2 = swipe_map[direction]
            device.swipe(x1, y1, x2, y2, duration=0.3)

        elif command == "swipe":
            x1, y1 = int(step_args["x1"]), int(step_args["y1"])
            x2, y2 = int(step_args["x2"]), int(step_args["y2"])
            dur = float(step_args.get("duration", 0.5))
            device.swipe(x1, y1, x2, y2, duration=dur)

        elif command == "captcha-swipe":
            from .input_ctrl import _generate_captcha_path, _verify_captcha_result
            x1, y1 = int(step_args["x1"]), int(step_args["y1"])
            x2, y2 = int(step_args["x2"]), int(step_args["y2"])
            points, total_dur = _generate_captcha_path(
                x1, y1, x2, y2,
                easing=step_args.get("easing", "human"),
                overshoot=int(step_args.get("overshoot", 0)),
                y_wobble=int(step_args.get("y_wobble", 0)),
                steps=int(step_args.get("steps", 30)),
                hold_start=float(step_args.get("hold_start", 0.12)),
                hold_end=float(step_args.get("hold_end", 0.08)),
                duration=float(step_args.get("duration", 0.8)),
            )
            device.swipe_points(points, duration=total_dur)
            if step_args.get("verify"):
                vr = _verify_captcha_result(device, wait_after=float(step_args.get("wait_after", 1.5)))
                if vr["passed"] is False:
                    raise RuntimeError(f"CAPTCHA failed: {vr['detail']}")

        elif command == "clear":
            el = device(focused=True)
            if el.exists:
                el.clear_text()
            else:
                raise RuntimeError("No focused input field")

        else:
            raise RuntimeError(f"Unknown input command: {command}")

    elif action == "wait":
        text = step_args.get("text", "")
        timeout = float(step_args.get("timeout", 10))
        interval = 0.5
        elapsed = 0
        if command == "text":
            while elapsed < timeout:
                if _find_element_by_text(device, text):
                    return
                time.sleep(interval)
                elapsed += interval
            raise RuntimeError(f'Text "{text}" not found within {timeout}s')
        elif command == "gone":
            while elapsed < timeout:
                if not _find_element_by_text(device, text):
                    return
                time.sleep(interval)
                elapsed += interval
            raise RuntimeError(f'Text "{text}" still present after {timeout}s')
        else:
            raise RuntimeError(f"Unknown wait command: {command}")

    elif action == "app":
        if command == "launch":
            pkg = step_args.get("package", "")
            device.app_start(pkg)
            time.sleep(0.5)
        elif command == "stop":
            pkg = step_args.get("package", "")
            device.app_stop(pkg)
        else:
            raise RuntimeError(f"Unknown app command: {command}")

    elif action == "ui":
        if command == "dump":
            xml_str = _get_ui_xml(device)
            root = _parse_xml(xml_str)
            nodes = _collect_interactive_nodes(root)
            _save_numbered_cache(nodes)
        else:
            raise RuntimeError(f"Unknown ui command: {command}")

    elif action == "shell":
        cmd_str = step_args.get("command", command)
        device.shell(cmd_str)

    elif action == "sleep":
        seconds = float(step_args.get("seconds", command or "1"))
        time.sleep(seconds)

    elif action == "device":
        if command == "screen-on":
            if not device.info.get("screenOn"):
                device.press("power")
                time.sleep(0.3)
        elif command == "unlock":
            w, h = cfg_mod.get_screen_size()
            device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
            time.sleep(0.3)
        else:
            raise RuntimeError(f"Unknown device command: {command}")

    else:
        raise RuntimeError(f"Unknown action: {action}. Supported: input, wait, app, ui, shell, sleep, device")
