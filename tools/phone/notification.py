"""Notification interaction: list, tap, reply, dismiss, expand/collapse."""

import re
import time

from .connection import get_device
from .utils import output, error, ok, warn, audit_log
from . import config as cfg


def _get_notifications(device, count=10):
    """Parse current notifications from dumpsys."""
    out = device.shell("dumpsys notification --noredact").output
    notifications = []
    current = {}
    idx = 0

    for line in out.split("\n"):
        line = line.strip()
        if "NotificationRecord" in line:
            if current:
                notifications.append(current)
            pkg_match = re.search(r'pkg=(\S+)', line)
            current = {
                "index": idx,
                "package": pkg_match.group(1) if pkg_match else "",
                "title": "",
                "text": "",
                "key": "",
            }
            key_match = re.search(r'key=(\S+)', line)
            if key_match:
                current["key"] = key_match.group(1)
            idx += 1
        elif "android.title=" in line:
            title_match = re.search(r'android\.title=(.+)', line)
            if title_match and current:
                current["title"] = title_match.group(1).strip()
        elif "android.text=" in line:
            text_match = re.search(r'android\.text=(.+)', line)
            if text_match and current:
                current["text"] = text_match.group(1).strip()

    if current:
        notifications.append(current)

    return notifications[:count]


def cmd_list(args):
    """List current notifications."""
    device = get_device(getattr(args, "device", None))
    count = int(getattr(args, "count", 10))

    notifications = _get_notifications(device, count)

    if not notifications:
        output("(no notifications)")
        return

    for n in notifications:
        line = f'[{n["index"]}] {n["package"]}'
        if n["title"]:
            line += f' | {n["title"]}'
        if n["text"]:
            line += f' | {n["text"][:60]}'
        output(line)

    output(f"\n[Total: {len(notifications)}]")
    audit_log(f"notification list count={count}")


def cmd_tap(args):
    """Tap/click a notification to open it."""
    device = get_device(getattr(args, "device", None))
    index = int(args.index)

    # Open notification shade first
    device.open_notification()
    time.sleep(0.5)

    # Get UI tree and find notification elements
    from .ui import _get_ui_xml, _parse_xml, _get_node_attrs, _parse_bounds_str
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)

    # Find notification items
    notif_nodes = []
    for node in root.iter():
        attrs = _get_node_attrs(node)
        if "notification" in attrs["class"].lower() or "Notification" in attrs.get("resource-id", ""):
            if attrs["clickable"]:
                notif_nodes.append(attrs)

    if index < len(notif_nodes):
        bounds = _parse_bounds_str(notif_nodes[index]["bounds"])
        if bounds:
            cx = (bounds[0] + bounds[2]) // 2
            cy = (bounds[1] + bounds[3]) // 2
            device.click(cx, cy)
            ok(f"Tapped notification #{index}")
        else:
            error(f"Cannot locate notification #{index}")
    else:
        # Fallback: tap by approximate position (proportional to screen size)
        w, h = cfg.get_screen_size()
        # Status bar ~8% of height, each notification ~5% of height
        y_start = int(h * 0.08)
        notif_height = int(h * 0.05)
        y_offset = y_start + index * notif_height + notif_height // 2
        device.click(w // 2, min(y_offset, h - int(h * 0.08)))
        ok(f"Tapped approximate notification area #{index}")
        warn("Used fallback positioning — verify result with ui dump")

    audit_log(f"notification tap {index}")


def cmd_reply(args):
    """Reply to a notification inline."""
    device = get_device(getattr(args, "device", None))
    index = int(args.index)
    content = args.content

    # Open notification shade
    device.open_notification()
    time.sleep(0.5)

    # Look for reply action
    from .ui import _get_ui_xml, _parse_xml, _get_node_attrs, _parse_bounds_str
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)

    # Try to find reply button/input
    for node in root.iter():
        attrs = _get_node_attrs(node)
        text_lower = (attrs["text"] + attrs["content-desc"]).lower()
        if "回复" in text_lower or "reply" in text_lower or "答复" in text_lower:
            bounds = _parse_bounds_str(attrs["bounds"])
            if bounds:
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                device.click(cx, cy)
                time.sleep(0.3)
                device.send_keys(content)
                time.sleep(0.15)
                device.press("enter")
                audit_log(f'notification reply {index} "{content[:20]}"')
                ok(f"Replied to notification #{index}")
                return

    error("Reply button not found. The notification may not support inline reply.")


def cmd_dismiss(args):
    """Dismiss/clear notification(s)."""
    device = get_device(getattr(args, "device", None))
    dismiss_all = getattr(args, "all", False)
    index = getattr(args, "index", None)

    if dismiss_all:
        # Open notification shade and tap "clear all"
        device.open_notification()
        time.sleep(0.5)
        # Swipe down to reveal clear all button
        w, h = cfg.get_screen_size()
        device.swipe(w // 2, int(h * 0.4), w // 2, int(h * 0.7), duration=0.3)
        time.sleep(0.3)

        # Look for clear/dismiss all button
        from .ui import _get_ui_xml, _parse_xml, _get_node_attrs, _parse_bounds_str
        xml_str = _get_ui_xml(device)
        root = _parse_xml(xml_str)

        for node in root.iter():
            attrs = _get_node_attrs(node)
            text_lower = (attrs["text"] + attrs["content-desc"]).lower()
            if any(k in text_lower for k in ["全部清除", "clear all", "清除", "dismiss"]):
                bounds = _parse_bounds_str(attrs["bounds"])
                if bounds and attrs["clickable"]:
                    cx = (bounds[0] + bounds[2]) // 2
                    cy = (bounds[1] + bounds[3]) // 2
                    device.click(cx, cy)
                    ok("All notifications dismissed")
                    audit_log("notification dismiss --all")
                    return

        # Fallback
        device.shell("service call notification 1")
        ok("Notifications cleared via service")
    elif index is not None:
        # Swipe away specific notification
        device.open_notification()
        time.sleep(0.5)
        w, h = cfg.get_screen_size()
        y_pos = 200 + int(index) * 120
        device.swipe(w * 3 // 4, y_pos, 0, y_pos, duration=0.3)
        ok(f"Dismissed notification #{index}")
    else:
        error("Specify notification index or --all")

    audit_log(f"notification dismiss {index or '--all'}")


def cmd_expand(args):
    """Expand notification shade."""
    device = get_device(getattr(args, "device", None))
    device.open_notification()
    audit_log("notification expand")
    ok("Notification shade expanded")


def cmd_collapse(args):
    """Collapse notification shade."""
    device = get_device(getattr(args, "device", None))
    device.press("back")
    audit_log("notification collapse")
    ok("Notification shade collapsed")
