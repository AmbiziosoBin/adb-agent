"""UI tree acquisition, simplification, element finding."""

import os
import re
import time
import json
from lxml import etree

from .connection import get_device, adb_shell
from .utils import output, error, truncate_text, center_of_bounds, is_json_mode, mark_output_handled
from . import config as cfg

# Cache last dump for diff
_last_dump_result = None

# Cache last numbered dump for tap-nth (preserves filter context)
# Uses file-based cache because each CLI invocation is a separate process
_last_numbered_nodes = None
_TAP_NTH_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".tap_nth_cache.json")


def _save_numbered_cache(nodes):
    """Save numbered node list to file for cross-process tap-nth."""
    import json
    try:
        # Store only what tap-nth needs: bounds for each node
        cache = []
        for attrs in nodes:
            bounds = _parse_bounds_str(attrs["bounds"])
            if bounds:
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                label = attrs.get("text") or attrs.get("content-desc") or attrs.get("class", "")
                cache.append({"cx": cx, "cy": cy, "label": label[:40]})
            else:
                cache.append(None)
        with open(_TAP_NTH_CACHE_FILE, "w") as f:
            json.dump({"nodes": cache, "ts": time.time()}, f)
    except Exception:
        pass


def get_cached_numbered_node(n):
    """Get the Nth node (1-indexed) from the last numbered dump file cache.
    Returns (cx, cy) or None. Cache expires after 60 seconds.
    """
    import json
    try:
        with open(_TAP_NTH_CACHE_FILE, "r") as f:
            data = json.load(f)
        # Expire after 60s
        if time.time() - data.get("ts", 0) > 60:
            return None
        nodes = data.get("nodes", [])
        if n < 1 or n > len(nodes):
            return None
        entry = nodes[n - 1]
        if entry is None:
            return None
        return entry["cx"], entry["cy"]
    except Exception:
        return None


def get_cached_numbered_count():
    """Return the number of cached numbered nodes, or 0 if no cache."""
    import json
    try:
        with open(_TAP_NTH_CACHE_FILE, "r") as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) > 60:
            return 0
        return len(data.get("nodes", []))
    except Exception:
        return 0


def _get_ui_xml(device, timeout=None):
    """Get raw UI hierarchy XML from device.
    
    Runs both native adb uiautomator dump and u2 dump_hierarchy,
    then returns whichever has more text content (more complete).
    """
    if timeout is None:
        timeout = cfg.get_timeout("ui_dump")

    native_xml = None
    u2_xml = None

    # Method 1: native adb uiautomator dump
    try:
        from .connection import adb_shell
        adb_shell("rm -f /data/local/tmp/ui_dump.xml")
        out, rc = adb_shell("uiautomator dump /data/local/tmp/ui_dump.xml")
        if rc == 0 and "dumped" in out.lower():
            xml_out, rc2 = adb_shell("cat /data/local/tmp/ui_dump.xml")
            if rc2 == 0 and xml_out.strip().startswith("<?xml"):
                native_xml = xml_out
    except Exception:
        pass

    # Method 2: u2 dump_hierarchy
    try:
        u2_xml = device.dump_hierarchy()
    except Exception:
        pass

    # Pick the one with more non-empty text attributes
    if native_xml and u2_xml:
        def _count_texts(xml_str):
            import re
            return len(re.findall(r'text="([^"]+)"', xml_str))
        if _count_texts(native_xml) >= _count_texts(u2_xml):
            return native_xml
        else:
            return u2_xml
    elif native_xml:
        return native_xml
    elif u2_xml:
        return u2_xml
    else:
        error("Failed to dump UI hierarchy: both methods failed")


def _parse_xml(xml_str):
    """Parse XML string to lxml element tree."""
    try:
        root = etree.fromstring(xml_str.encode("utf-8"))
        return root
    except Exception as e:
        error(f"Failed to parse UI XML: {e}")


def _get_node_attrs(node):
    """Extract useful attributes from a UI node."""
    return {
        "class": (node.get("class") or "").split(".")[-1],
        "text": node.get("text", ""),
        "resource-id": node.get("resource-id", ""),
        "content-desc": node.get("content-desc", ""),
        "package": node.get("package", ""),
        "bounds": node.get("bounds", ""),
        "clickable": node.get("clickable") == "true",
        "focusable": node.get("focusable") == "true",
        "checkable": node.get("checkable") == "true",
        "checked": node.get("checked") == "true",
        "scrollable": node.get("scrollable") == "true",
        "selected": node.get("selected") == "true",
        "enabled": node.get("enabled") == "true",
        "focused": node.get("focused") == "true",
        "long-clickable": node.get("long-clickable") == "true",
        "password": node.get("password") == "true",
    }


def _parse_bounds_str(bounds_str):
    """Parse '[x1,y1][x2,y2]' to (x1, y1, x2, y2)."""
    m = re.findall(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
    if m:
        return tuple(int(x) for x in m[0])
    return None


def _short_id(resource_id):
    """Shorten resource-id: 'com.foo.bar:id/abc' -> 'abc'."""
    if resource_id and "/" in resource_id:
        return resource_id.split("/")[-1]
    return resource_id


def _is_interactive(attrs):
    """Check if node is interactive."""
    return attrs["clickable"] or attrs["focusable"] or attrs["checkable"] or attrs["scrollable"]


def _has_content(attrs):
    """Check if node has visible text content."""
    return bool(attrs["text"] or attrs["content-desc"])


def _node_in_rect(attrs, rect):
    """Check if node bounds overlap with given rect."""
    bounds = _parse_bounds_str(attrs["bounds"])
    if not bounds:
        return False
    x1, y1, x2, y2 = rect
    bx1, by1, bx2, by2 = bounds
    return not (bx2 < x1 or bx1 > x2 or by2 < y1 or by1 > y2)


def _format_node_compact(attrs):
    """Format a single node in compact one-line format."""
    parts = []
    cls = attrs["class"]
    text = attrs["text"]
    desc = attrs["content-desc"]
    rid = _short_id(attrs["resource-id"])
    bounds = _parse_bounds_str(attrs["bounds"])

    label = text or desc or ""
    label = truncate_text(label)

    flags = []
    if attrs["clickable"]:
        flags.append("click")
    if attrs["scrollable"]:
        flags.append("scroll")
    if attrs["focusable"] and not attrs["clickable"]:
        flags.append("focus")
    if attrs["checkable"]:
        flags.append("check")
    if attrs["checked"]:
        flags.append("checked")
    if attrs["selected"]:
        flags.append("selected")
    if attrs["focused"]:
        flags.append("focused")
    if attrs["password"]:
        flags.append("pwd")

    line = f'[{cls}'
    if label:
        line += f' "{label}"'
    if rid:
        line += f' id:{rid}'
    if flags:
        line += f' {" ".join(flags)}'
    if bounds:
        line += f' ({bounds[0]},{bounds[1]})({bounds[2]},{bounds[3]})'
    line += "]"
    return line


def _format_tree(node, depth=0, max_depth=20, filters=None):
    """Format UI tree recursively in readable tree format."""
    if depth > max_depth:
        return []

    attrs = _get_node_attrs(node)
    lines = []

    # Apply filters
    show = True
    if filters:
        if filters.get("interactive") and not _is_interactive(attrs):
            show = False
        if filters.get("text_only") and not _has_content(attrs):
            show = False
        if filters.get("package") and attrs["package"] != filters["package"]:
            show = False
        if filters.get("search"):
            kw = filters["search"].lower()
            searchable = f'{attrs["text"]} {attrs["content-desc"]} {attrs["resource-id"]}'.lower()
            if kw not in searchable:
                show = False
        if filters.get("rect") and not _node_in_rect(attrs, filters["rect"]):
            show = False

    if show and (attrs["class"] or _has_content(attrs) or _is_interactive(attrs)):
        prefix = "│  " * depth + "├─ " if depth > 0 else ""
        cls = attrs["class"]
        text = truncate_text(attrs["text"])
        desc = truncate_text(attrs["content-desc"])
        rid = _short_id(attrs["resource-id"])
        bounds = _parse_bounds_str(attrs["bounds"])

        parts = [cls]
        if text:
            parts.append(f'"{text}"')
        elif desc:
            parts.append(f'desc:"{desc}"')
        if rid:
            parts.append(f'id:{rid}')

        flags = []
        if attrs["clickable"]:
            flags.append("[click]")
        if attrs["scrollable"]:
            flags.append("[scroll]")
        if attrs["selected"]:
            flags.append("[selected]")
        if attrs["focused"]:
            flags.append("[focused]")
        if attrs["checked"]:
            flags.append("[checked]")
        if attrs["password"]:
            flags.append("[pwd]")

        if flags:
            parts.extend(flags)
        if bounds:
            parts.append(f'({bounds[0]},{bounds[1]})({bounds[2]},{bounds[3]})')

        line = prefix + " ".join(parts)
        lines.append(line)

    for child in node:
        lines.extend(_format_tree(child, depth + 1, max_depth, filters))

    return lines


def _collect_interactive_nodes(root, filters=None):
    """Collect interactive and content nodes for numbered listing.
    
    When 'interactive' filter is set, shows ALL nodes that are either
    interactive OR have text content, with interactive ones marked by flags.
    This gives AI full context (titles, labels) while highlighting clickable elements.
    """
    results = []
    for node in root.iter():
        attrs = _get_node_attrs(node)
        # Include if interactive OR has visible text/description
        if not _is_interactive(attrs) and not _has_content(attrs):
            continue

        # Apply additional filters
        if filters:
            if filters.get("search"):
                kw = filters["search"].lower()
                searchable = f'{attrs["text"]} {attrs["content-desc"]} {attrs["resource-id"]}'.lower()
                if kw not in searchable:
                    continue
            if filters.get("rect") and not _node_in_rect(attrs, filters["rect"]):
                continue
            if filters.get("package") and attrs["package"] != filters["package"]:
                continue
            if filters.get("text_only") and not _has_content(attrs):
                continue

        results.append(attrs)
    return results


def _get_current_info(device):
    """Get current activity and package name."""
    try:
        info = device.app_current()
        return info.get("package", ""), info.get("activity", "")
    except Exception:
        return "", ""


def _get_screen_state(device):
    """Get screen on/off state and basic device info."""
    try:
        info = device.info
        w = info.get("displayWidth", 0)
        h = info.get("displayHeight", 0)
        screen_on = info.get("screenOn", False)
        return w, h, screen_on
    except Exception:
        return 0, 0, False


# ─── Public Commands ───


def cmd_dump(args):
    """Dump UI tree with various filtering options."""
    global _last_dump_result

    device = get_device(args.device if hasattr(args, "device") else None)
    timeout = getattr(args, "timeout", None)
    xml_str = _get_ui_xml(device, timeout=timeout)
    root = _parse_xml(xml_str)

    pkg, activity = _get_current_info(device)
    w, h, screen_on = _get_screen_state(device)

    # Build filter dict
    filters = {}
    if getattr(args, "interactive", False):
        filters["interactive"] = True
    if getattr(args, "text", False):
        filters["text_only"] = True
    if getattr(args, "package", None):
        filters["package"] = args.package
    if getattr(args, "search", None):
        filters["search"] = args.search
    if getattr(args, "rect", None):
        try:
            parts = args.rect.split(",")
            filters["rect"] = tuple(int(x) for x in parts)
        except Exception:
            error("Invalid rect format. Use: x1,y1,x2,y2")

    max_depth = getattr(args, "depth", None) or cfg.load_config()["output"]["max_ui_depth"]

    # Header (used for tree mode and _last_dump_result)
    header = f"[当前] {pkg}"
    if activity:
        header += f" / {activity}"
    header += f"\n[屏幕 {w}x{h}] [{'亮' if screen_on else '灭'}]"

    # Detect scrollable containers for hint output
    def _detect_scroll_direction(node):
        """Detect scroll direction (horizontal/vertical) from child layout."""
        children = list(node)
        if len(children) < 2:
            return "vertical"  # default assumption

        # Parse bounds of direct children
        child_bounds = []
        for c in children:
            b = c.get("bounds", "")
            m = re.findall(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', b)
            if m:
                child_bounds.append(tuple(int(x) for x in m[0]))

        if len(child_bounds) < 2:
            return "vertical"

        # Check if children share the same y range (horizontal) or same x range (vertical)
        y_tops = [b[1] for b in child_bounds]
        x_lefts = [b[0] for b in child_bounds]
        y_range = max(y_tops) - min(y_tops)
        x_range = max(x_lefts) - min(x_lefts)

        if x_range > y_range and y_range < 50:
            return "horizontal"
        return "vertical"

    def _get_child_labels(node, max_labels=3):
        """Get text labels from direct children for hint context."""
        labels = []
        for c in node.iter():
            if c == node:
                continue
            text = c.get("text", "").strip()
            if text and text not in labels:
                labels.append(text)
                if len(labels) >= max_labels:
                    break
        return labels

    def _detect_scroll_hints(root):
        """Return list of structured hint dicts for all scrollable containers."""
        hints = []
        seen_bounds = set()  # deduplicate nested scrollable containers

        for node in root.iter():
            if node.get("scrollable") != "true":
                continue

            bounds_str = node.get("bounds", "")
            if bounds_str in seen_bounds:
                continue
            seen_bounds.add(bounds_str)

            cls = (node.get("class") or "").split(".")[-1]
            direction = _detect_scroll_direction(node)
            pb = re.findall(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)

            if direction == "horizontal":
                labels = _get_child_labels(node)
                label_hint = "、".join(labels) if labels else cls
                if pb:
                    px1, py1, px2, py2 = (int(x) for x in pb[0])
                    cy = (py1 + py2) // 2
                    swipe_from_x = px2 - 30
                    swipe_to_x = px1 + 30
                    hints.append({
                        "direction": "horizontal",
                        "widget": label_hint,
                        "swipeCommand": f"input swipe {swipe_from_x} {cy} {swipe_to_x} {cy}",
                        "note": "Hidden buttons may exist on right (delete, report, etc.)"
                    })
                else:
                    hints.append({
                        "direction": "horizontal",
                        "widget": label_hint,
                        "note": "Hidden buttons may exist on right. Try horizontal swipe."
                    })
            else:
                if pb:
                    px1, py1, px2, py2 = (int(x) for x in pb[0])
                    cx = (px1 + px2) // 2
                    swipe_from = int(py1 + (py2 - py1) * 0.75)
                    swipe_to = int(py1 + (py2 - py1) * 0.25)
                    hints.append({
                        "direction": "vertical",
                        "widget": cls,
                        "swipeCommand": f"input swipe {cx} {swipe_from} {cx} {swipe_to}",
                        "note": "Only visible portion. Max 1-2 scrolls for feeds."
                    })
                else:
                    hints.append({
                        "direction": "vertical",
                        "widget": cls,
                        "note": "Only visible portion. Max 1-2 scrolls for feeds."
                    })

        return hints

    def _format_hint_text(hint):
        """Format structured hint dict to text string for tree mode."""
        swipe_cmd = hint.get("swipeCommand", "")
        direction = "Horizontal" if hint["direction"] == "horizontal" else "Vertical"
        text = f"[Hint] {direction} scrollable ({hint['widget']}). {hint['note']}"
        if swipe_cmd:
            text += f" Swipe: '{swipe_cmd}'"
        return text

    # Generate scroll hints early
    scroll_hints = _detect_scroll_hints(root)

    if getattr(args, "numbered", False):
        # Numbered mode: output scroll hints as prominent text BEFORE JSON
        nodes = _collect_interactive_nodes(root, filters)

        for hint in scroll_hints:
            swipe_cmd = hint.get("swipeCommand", "")
            if hint["direction"] == "vertical":
                tip = f"[重要提示] 纵向可滚动({hint['widget']})，当前仅显示可见部分。"
                if swipe_cmd:
                    tip += f"如需查看更多: '{swipe_cmd}'。"
                tip += "信息流应用避免死循环，最多滚动1-2次。"
            else:
                tip = f"[重要提示] 横向可滚动({hint['widget']})，右侧可能有隐藏按钮(如删除、举报等)。"
                if swipe_cmd:
                    tip += f"如果找不到某些按钮，可以尝试水平滑动查看: '{swipe_cmd}'"
            print(tip)

        # Build JSON structure (no hints inside, they're already printed above)
        result = {}
        result["package"] = pkg
        if activity:
            result["activity"] = activity
        result["screen"] = {"width": w, "height": h}
        if not screen_on:
            result["screenOn"] = False

        elements = []
        for i, attrs in enumerate(nodes, 1):
            node_text = truncate_text(attrs["text"])
            desc = truncate_text(attrs["content-desc"])
            rid = _short_id(attrs["resource-id"])

            el = {"index": i, "class": attrs["class"]}

            # Split text sources into separate fields
            if node_text:
                el["text"] = node_text
            if desc:
                el["desc"] = desc
            if not node_text and not desc and rid:
                el["resourceId"] = rid

            bounds = _parse_bounds_str(attrs["bounds"])
            if bounds:
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                el["center"] = [cx, cy]

            # clickable always explicit; others only when true
            el["clickable"] = bool(attrs["clickable"])
            if attrs["scrollable"]:
                el["scrollable"] = True
            if attrs["selected"]:
                el["selected"] = True
            if attrs["checked"]:
                el["checked"] = True

            elements.append(el)

        result["elements"] = elements

        # Output compact JSON directly (bypass flush_json_result wrapper)
        json_str = json.dumps(result, ensure_ascii=False, separators=(',', ':'))
        print(json_str)

        _save_numbered_cache(nodes)
        _last_dump_result = {"header": header, "nodes": nodes, "mode": "numbered"}
        mark_output_handled()

    else:
        # Tree mode: text output with header and hints
        output(header)
        for hint in scroll_hints:
            output(_format_hint_text(hint))

        lines = _format_tree(root, max_depth=max_depth, filters=filters)
        for line in lines:
            output(line)
        _last_dump_result = {"header": header, "lines": lines, "mode": "tree"}


def cmd_find(args):
    """Find element by selector and return its info + center coordinates."""
    device = get_device(args.device if hasattr(args, "device") else None)
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)

    selector_type = args.selector_type  # text, id, class, desc
    value = args.value

    for node in root.iter():
        attrs = _get_node_attrs(node)
        match = False
        if selector_type == "text" and value in attrs["text"]:
            match = True
        elif selector_type == "id" and value in attrs["resource-id"]:
            match = True
        elif selector_type == "class" and value in attrs["class"]:
            match = True
        elif selector_type == "desc" and value in attrs["content-desc"]:
            match = True

        if match:
            bounds = _parse_bounds_str(attrs["bounds"])
            center = center_of_bounds(bounds) if bounds else None
            output(f'class: {attrs["class"]}')
            output(f'text: {attrs["text"]}')
            output(f'desc: {attrs["content-desc"]}')
            output(f'id: {attrs["resource-id"]}')
            output(f'bounds: {attrs["bounds"]}')
            if center:
                output(f'center: ({center[0]},{center[1]})')
            output(f'clickable: {attrs["clickable"]}')
            output(f'scrollable: {attrs["scrollable"]}')
            return

    output(f"[NOT FOUND] {selector_type}={value}")


def cmd_exists(args):
    """Check if element exists. Returns true/false."""
    device = get_device(args.device if hasattr(args, "device") else None)
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)

    selector_type = args.selector_type
    value = args.value

    for node in root.iter():
        attrs = _get_node_attrs(node)
        if selector_type == "text" and value in attrs["text"]:
            output("true")
            return
        elif selector_type == "id" and value in attrs["resource-id"]:
            output("true")
            return

    output("false")


def cmd_current(args):
    """Quick return current Activity + package + screen state (lightweight)."""
    device = get_device(args.device if hasattr(args, "device") else None)
    pkg, activity = _get_current_info(device)
    w, h, screen_on = _get_screen_state(device)

    try:
        battery = device.shell("dumpsys battery | grep level").output.strip()
        level = re.search(r'level:\s*(\d+)', battery)
        bat_str = f"{level.group(1)}%" if level else "N/A"
    except Exception:
        bat_str = "N/A"

    output(f"package: {pkg}")
    output(f"activity: {activity}")
    output(f"screen: {'on' if screen_on else 'off'}")
    output(f"resolution: {w}x{h}")
    output(f"battery: {bat_str}")


def cmd_watch(args):
    """Monitor UI changes (basic popup detection)."""
    device = get_device(args.device if hasattr(args, "device") else None)
    duration = getattr(args, "duration", 10)
    interval = 2
    elapsed = 0

    prev_pkg = ""
    output(f"[Watching UI for {duration}s...]")

    while elapsed < duration:
        try:
            pkg, activity = _get_current_info(device)
            if pkg != prev_pkg and prev_pkg:
                output(f"[{elapsed}s] App changed: {prev_pkg} -> {pkg} / {activity}")
            prev_pkg = pkg
        except Exception:
            output(f"[{elapsed}s] Connection lost")
            break
        time.sleep(interval)
        elapsed += interval

    output("[Watch ended]")


def cmd_diff(args):
    """Compare current UI with last dump."""
    global _last_dump_result

    if _last_dump_result is None:
        error("No previous dump to compare. Run 'ui dump' first.")

    device = get_device(args.device if hasattr(args, "device") else None)
    xml_str = _get_ui_xml(device)
    root = _parse_xml(xml_str)

    pkg, activity = _get_current_info(device)
    output(f"[当前] {pkg} / {activity}")

    # Collect current nodes
    current_nodes = _collect_interactive_nodes(root)
    current_texts = {(a["text"], a["content-desc"], a["resource-id"]) for a in current_nodes}

    if _last_dump_result.get("nodes"):
        prev_nodes = _last_dump_result["nodes"]
        prev_texts = {(a["text"], a["content-desc"], a["resource-id"]) for a in prev_nodes}

        added = current_texts - prev_texts
        removed = prev_texts - current_texts

        if not added and not removed:
            output("[No changes detected]")
        else:
            if added:
                output(f"[+ Added {len(added)} elements]")
                for text, desc, rid in list(added)[:10]:
                    label = text or desc or _short_id(rid) or "?"
                    output(f"  + {label}")
            if removed:
                output(f"[- Removed {len(removed)} elements]")
                for text, desc, rid in list(removed)[:10]:
                    label = text or desc or _short_id(rid) or "?"
                    output(f"  - {label}")
    else:
        output("[Previous dump was in tree mode, cannot diff. Run numbered/compact dump first.]")
