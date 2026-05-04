"""File management: push, pull, list, delete, screenshot, screenrecord."""

import os
import re
import time
import datetime

from .connection import get_device, adb_command, adb_shell
from .utils import output, error, ok, audit_log, format_size, is_json_mode


def _is_json_mode():
    """Check if JSON output mode is active."""
    return is_json_mode()


def _append_output(message):
    """Append to JSON output data array (for JSON mode MEDIA: lines)."""
    from .utils import _output_lines
    _output_lines.append(str(message))


def cmd_push(args):
    """Push file to phone."""
    local_path = args.local_path
    remote_path = args.remote_path

    if not os.path.exists(local_path):
        error(f"Local file not found: {local_path}")

    out, rc = adb_command("push", local_path, remote_path, device_serial=getattr(args, "device", None))
    if rc != 0:
        error(f"Push failed: {out}")
    audit_log(f"file push {local_path} -> {remote_path}")
    ok(f"Pushed to {remote_path}")


def cmd_pull(args):
    """Pull file from phone."""
    remote_path = args.remote_path
    local_path = getattr(args, "local_path", None) or os.path.basename(remote_path)

    out, rc = adb_command("pull", remote_path, local_path, device_serial=getattr(args, "device", None))
    if rc != 0:
        error(f"Pull failed: {out}")
    audit_log(f"file pull {remote_path} -> {local_path}")
    ok(f"Pulled to {local_path}")


def cmd_ls(args):
    """List directory on phone."""
    device = get_device(getattr(args, "device", None))
    remote_path = args.remote_path
    detail = getattr(args, "detail", False)

    if detail:
        out = device.shell(f"ls -la {remote_path}").output
    else:
        out = device.shell(f"ls {remote_path}").output

    output(out.strip())
    audit_log(f"file ls {remote_path}")


def cmd_rm(args):
    """Delete file on phone."""
    if not getattr(args, "confirm", False):
        error("Delete requires --confirm flag for safety")

    device = get_device(getattr(args, "device", None))
    remote_path = args.remote_path
    device.shell(f"rm -rf {remote_path}")
    audit_log(f"file rm {remote_path}")
    ok(f"Deleted {remote_path}")


def cmd_mkdir(args):
    """Create directory on phone."""
    device = get_device(getattr(args, "device", None))
    remote_path = args.remote_path
    device.shell(f"mkdir -p {remote_path}")
    audit_log(f"file mkdir {remote_path}")
    ok(f"Created {remote_path}")


def cmd_cat(args):
    """View file content on phone."""
    device = get_device(getattr(args, "device", None))
    remote_path = args.remote_path
    out = device.shell(f"cat {remote_path}").output
    output(out)
    audit_log(f"file cat {remote_path}")


def cmd_stat(args):
    """File info on phone."""
    device = get_device(getattr(args, "device", None))
    remote_path = args.remote_path
    out = device.shell(f"stat {remote_path}").output
    output(out.strip())
    audit_log(f"file stat {remote_path}")


def _take_screenshot_u2(device, filepath, quality=80):
    """Take screenshot via uiautomator2. Returns PIL Image or None."""
    try:
        img = device.screenshot()
        img.save(filepath, quality=quality)
        return img
    except Exception:
        return None


def _take_screenshot_adb(filepath, device_serial=None):
    """Fallback: take screenshot via adb screencap. Returns PIL Image or None."""
    import subprocess
    try:
        conf_mod = __import__("phone.config", fromlist=["load_config"])
        conf = conf_mod.load_config()
        serial = device_serial or conf.get("device", "")
        serial_args = ["-s", serial] if serial else []
        result = subprocess.run(
            ["adb"] + serial_args + ["exec-out", "screencap", "-p"],
            capture_output=True, timeout=10
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            with open(filepath, "wb") as f:
                f.write(result.stdout)
            from PIL import Image
            return Image.open(filepath)
    except Exception:
        pass
    return None


def _deliver_screenshot(filepath, img, for_ai):
    """Output screenshot result in the appropriate format."""
    if for_ai:
        import base64
        import io
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        output(f"IMAGE_BASE64:{b64}")
        ok(f"Screenshot for AI analysis: {filepath} ({img.size[0]}x{img.size[1]} full resolution)")
    else:
        # MEDIA: MUST be a standalone raw line in stdout so OpenClaw's
        # splitMediaFromOutput can detect it. Always print directly.
        print(f"MEDIA:{filepath}")
        ok(f"Screenshot saved: {filepath}")


def cmd_screenshot(args):
    """Take screenshot. Saves to OpenClaw media dir so it can be sent to user.
    Uses u2 with retry, falls back to adb screencap if u2 fails."""
    device = get_device(getattr(args, "device", None))
    filename = getattr(args, "filename", None)
    quality = int(getattr(args, "quality", 80))
    element_selector = getattr(args, "element", None)
    for_ai = getattr(args, "for_ai", False)

    if not filename:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{ts}.png"

    media_dir = os.path.expanduser("~/.openclaw/media/phone")
    os.makedirs(media_dir, exist_ok=True)
    filepath = os.path.join(media_dir, filename)

    if element_selector:
        # Element screenshot (no adb fallback possible)
        el = device(text=element_selector)
        if not el.exists:
            el = device(resourceId=element_selector)
        if not el.exists:
            el = device(description=element_selector)
        if el.exists:
            try:
                img = el.screenshot()
                img.save(filepath)
            except Exception as e:
                error(f"Element screenshot failed: {e}")
            _deliver_screenshot(filepath, img, for_ai)
        else:
            error(f'Element "{element_selector}" not found')
    else:
        actual_quality = 100 if for_ai else quality
        img = None

        # Try u2 screenshot with retry (max 2 attempts)
        for attempt in range(2):
            img = _take_screenshot_u2(device, filepath, actual_quality)
            if img:
                break
            time.sleep(0.5)

        # Fallback to adb screencap
        if not img:
            img = _take_screenshot_adb(filepath, getattr(args, "device", None))

        if not img:
            error("Screenshot failed: both u2 and adb screencap methods failed. Check device connection.")

        _deliver_screenshot(filepath, img, for_ai)

    audit_log(f"screenshot {filepath} for_ai={for_ai}")


def cmd_screenrecord_start(args):
    """Start screen recording."""
    device = get_device(getattr(args, "device", None))
    filename = getattr(args, "filename", None)
    duration = int(getattr(args, "duration", 30))

    if not filename:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenrecord_{ts}.mp4"

    remote_path = f"/sdcard/{filename}"
    device.shell(f"screenrecord --time-limit {duration} {remote_path} &")
    audit_log(f"screenrecord start {remote_path} duration={duration}")
    ok(f"Recording started: {remote_path} (max {duration}s)")
    output(f"Run 'screenrecord stop' to stop and pull the file")


def cmd_screenrecord_stop(args):
    """Stop screen recording and pull file."""
    device = get_device(getattr(args, "device", None))

    # Kill screenrecord process
    device.shell("pkill -f screenrecord")
    time.sleep(0.5)

    # Find the recording file
    out = device.shell("ls -t /sdcard/screenrecord_*.mp4 2>/dev/null | head -1").output.strip()
    if out:
        local_name = os.path.basename(out)
        adb_command("pull", out, local_name, device_serial=getattr(args, "device", None))
        ok(f"Recording saved: {local_name}")
    else:
        ok("Recording stopped (file may need manual retrieval)")
    audit_log("screenrecord stop")
