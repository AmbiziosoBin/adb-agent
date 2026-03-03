"""Input method (IME) management: detect, switch, restore, handle ColorOS popups."""

import time
import re

from .connection import get_device
from .utils import output, error, ok, warn, audit_log
from .ui import _get_ui_xml, _parse_xml, _get_node_attrs, _parse_bounds_str

# Store original IME for restore
_original_ime = None

FAST_INPUT_IME = "com.github.uiautomator/.FastInputIME"


def _get_current_ime(device):
    """Get current default IME id."""
    out = device.shell("settings get secure default_input_method").output.strip()
    return out


def _set_ime(device, ime_id):
    """Set default IME."""
    device.shell(f"ime set {ime_id}")


def _is_fast_ime(ime_id):
    """Check if given IME is FastInputIME."""
    return "FastInputIME" in ime_id


def _handle_ime_switch_popup(device, max_wait=3):
    """Handle ColorOS 'switch input method' popup if it appears."""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            xml_str = _get_ui_xml(device, timeout=3)
            root = _parse_xml(xml_str)
            for node in root.iter():
                attrs = _get_node_attrs(node)
                text = (attrs["text"] + attrs["content-desc"]).lower()
                if any(kw in text for kw in ["确定", "确认", "允许", "ok", "同意", "切换"]):
                    if attrs["clickable"]:
                        bounds = _parse_bounds_str(attrs["bounds"])
                        if bounds:
                            cx = (bounds[0] + bounds[2]) // 2
                            cy = (bounds[1] + bounds[3]) // 2
                            device.click(cx, cy)
                            time.sleep(0.2)
                            return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def cmd_detect(args):
    """Detect and display current IME."""
    device = get_device(getattr(args, "device", None))
    current = _get_current_ime(device)
    is_fast = _is_fast_ime(current)
    output(f"current: {current}")
    output(f"is_fast_ime: {is_fast}")
    audit_log("ime detect")


def cmd_switch_to_fast(args):
    """Switch to FastInputIME for u2 text input."""
    global _original_ime
    device = get_device(getattr(args, "device", None))
    keep_ime = getattr(args, "keep_ime", False)

    if keep_ime:
        output("--keep-ime: skipping IME switch")
        return

    current = _get_current_ime(device)

    if _is_fast_ime(current):
        ok("Already using FastInputIME")
        return

    # Save original IME
    _original_ime = current
    output(f"Saving original IME: {current}")

    # Enable and set FastInputIME
    device.shell(f"ime enable {FAST_INPUT_IME}")
    _set_ime(device, FAST_INPUT_IME)
    time.sleep(0.3)

    # Handle potential ColorOS popup
    _handle_ime_switch_popup(device)

    # Verify
    new_ime = _get_current_ime(device)
    if _is_fast_ime(new_ime):
        ok("Switched to FastInputIME")
    else:
        warn(f"IME switch may have failed. Current: {new_ime}")

    audit_log(f"ime switch-to-fast (was: {current})")


def cmd_restore(args):
    """Restore original IME after operations."""
    global _original_ime
    device = get_device(getattr(args, "device", None))
    keep_ime = getattr(args, "keep_ime", False)

    if keep_ime:
        output("--keep-ime: skipping IME restore")
        return

    ime_id = getattr(args, "ime_id", None) or _original_ime

    if not ime_id:
        # Try to find a reasonable default
        out = device.shell("ime list -s").output
        imes = [line.strip() for line in out.strip().split("\n") if line.strip() and "FastInput" not in line]
        if imes:
            ime_id = imes[0]
            output(f"No saved IME, using first available: {ime_id}")
        else:
            error("No IME to restore to. Run 'device ime list' to see available IMEs.")

    _set_ime(device, ime_id)
    time.sleep(0.3)

    # Handle potential popup
    _handle_ime_switch_popup(device)

    # Verify
    new_ime = _get_current_ime(device)
    if ime_id in new_ime:
        ok(f"IME restored to {ime_id}")
    else:
        warn(f"IME restore may have failed. Current: {new_ime}")

    _original_ime = None
    audit_log(f"ime restore -> {ime_id}")


def cmd_auto_switch(args):
    """Auto switch to FastInputIME, do text input, then restore."""
    global _original_ime
    device = get_device(getattr(args, "device", None))

    current = _get_current_ime(device)
    need_switch = not _is_fast_ime(current)

    if need_switch:
        _original_ime = current
        device.shell(f"ime enable {FAST_INPUT_IME}")
        _set_ime(device, FAST_INPUT_IME)
        time.sleep(0.2)
        _handle_ime_switch_popup(device)

    # Input the text
    text = getattr(args, "text", "")
    if text:
        device.send_keys(text)
        ok(f"Typed text ({len(text)} chars)")

    # Restore if we switched
    if need_switch and _original_ime:
        time.sleep(0.15)
        _set_ime(device, _original_ime)
        _handle_ime_switch_popup(device)
        _original_ime = None

    audit_log(f"ime auto-switch text={len(text) if text else 0} chars")
