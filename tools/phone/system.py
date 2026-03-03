"""System information and monitoring: processes, memory, storage, CPU, network, logcat."""

import re

from .connection import get_device
from .utils import output, error, audit_log


def cmd_processes(args):
    """List running processes."""
    device = get_device(getattr(args, "device", None))
    top_n = int(getattr(args, "top", 10))
    out = device.shell(f"top -n 1 -b | head -{top_n + 1}").output
    output(out.strip())
    audit_log(f"sys processes --top {top_n}")


def cmd_memory(args):
    """Memory usage info."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("cat /proc/meminfo | head -6").output
    for line in out.strip().split("\n"):
        line = line.strip()
        if line:
            output(line)
    audit_log("sys memory")


def cmd_storage(args):
    """Storage usage info."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("df -h /data /sdcard /system 2>/dev/null").output
    output(out.strip())
    audit_log("sys storage")


def cmd_cpu(args):
    """CPU usage info."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("top -n 1 -b | head -5").output
    output(out.strip())

    # CPU info
    cpu_info = device.shell("cat /proc/cpuinfo | grep -E 'processor|model name|Hardware' | head -8").output
    if cpu_info.strip():
        output("\n" + cpu_info.strip())
    audit_log("sys cpu")


def cmd_network(args):
    """Network status info."""
    device = get_device(getattr(args, "device", None))

    # IP addresses
    ip_out = device.shell("ip addr show wlan0 2>/dev/null | grep 'inet '").output
    ip_match = re.search(r'inet\s+([\d.]+)', ip_out)
    output(f"WiFi IP: {ip_match.group(1) if ip_match else 'N/A'}")

    # Connection type
    conn_out = device.shell("dumpsys connectivity | grep 'Active default network'").output
    output(f"Connection: {conn_out.strip() or 'N/A'}")

    # WiFi info
    wifi_out = device.shell("dumpsys wifi | grep 'mWifiInfo'").output
    ssid_match = re.search(r'SSID:\s*"?([^",]+)', wifi_out)
    rssi_match = re.search(r'RSSI:\s*(-?\d+)', wifi_out)
    link_match = re.search(r'Link speed:\s*(\d+)', wifi_out)
    if ssid_match:
        output(f"SSID: {ssid_match.group(1)}")
    if rssi_match:
        output(f"Signal: {rssi_match.group(1)} dBm")
    if link_match:
        output(f"Link speed: {link_match.group(1)} Mbps")

    # Traffic stats
    rx = device.shell("cat /proc/net/dev | grep wlan0").output
    if rx.strip():
        parts = rx.strip().split()
        if len(parts) >= 10:
            rx_bytes = int(parts[1]) if parts[1].isdigit() else 0
            tx_bytes = int(parts[9]) if parts[9].isdigit() else 0
            output(f"RX: {rx_bytes / 1024 / 1024:.1f} MB  TX: {tx_bytes / 1024 / 1024:.1f} MB")

    audit_log("sys network")


def cmd_props(args):
    """System properties query."""
    device = get_device(getattr(args, "device", None))
    keyword = getattr(args, "keyword", None)

    if keyword:
        out = device.shell(f"getprop | grep -i '{keyword}'").output
    else:
        out = device.shell("getprop").output
    output(out.strip())
    audit_log(f"sys props {keyword or ''}")


def cmd_logcat(args):
    """View system logs."""
    device = get_device(getattr(args, "device", None))
    lines_count = int(getattr(args, "lines", 20))
    level = getattr(args, "level", None)
    tag_filter = getattr(args, "filter", None)
    app_pkg = getattr(args, "app", None)

    cmd = "logcat -d"
    if tag_filter:
        cmd += f" -s {tag_filter}"
    if level:
        level_map = {"verbose": "V", "debug": "D", "info": "I", "warn": "W", "error": "E", "fatal": "F"}
        l = level_map.get(level.lower(), level.upper())
        cmd += f" *:{l}"

    cmd += f" | tail -{lines_count}"

    if app_pkg:
        # Get PID first
        pid_out = device.shell(f"pidof {app_pkg}").output.strip()
        if pid_out:
            cmd = f"logcat -d --pid={pid_out} | tail -{lines_count}"
        else:
            output(f"[WARN] App {app_pkg} not running, showing all logs")

    out = device.shell(cmd).output
    output(out.strip())
    audit_log(f"sys logcat lines={lines_count}")


def cmd_notifications(args):
    """List or clear notifications."""
    device = get_device(getattr(args, "device", None))
    clear = getattr(args, "clear", False)

    if clear:
        device.shell("service call notification 1")
        ok_msg = "Notifications cleared"
        output(ok_msg)
    else:
        out = device.shell("dumpsys notification --noredact | grep -E 'pkg=|android.title|android.text' | head -30").output
        if out.strip():
            output(out.strip())
        else:
            output("(no notifications)")
    audit_log(f"sys notifications {'--clear' if clear else ''}")


def cmd_settings(args):
    """Read/write system settings."""
    device = get_device(getattr(args, "device", None))
    namespace = args.namespace  # system, secure, global
    action = args.action  # get, put
    key = args.key
    value = getattr(args, "value", None)

    if namespace not in ("system", "secure", "global"):
        error("Namespace must be: system, secure, or global")

    if action == "get":
        out = device.shell(f"settings get {namespace} {key}").output
        output(out.strip())
    elif action == "put":
        if value is None:
            error("Value required for 'put' action")
        device.shell(f"settings put {namespace} {key} {value}")
        output(f"[OK] {namespace}/{key} = {value}")
    else:
        error("Action must be: get or put")
    audit_log(f"sys settings {namespace} {action} {key} {value or ''}")


def cmd_date(args):
    """View or set system date/time."""
    device = get_device(getattr(args, "device", None))
    set_time = getattr(args, "set", None)

    if set_time:
        device.shell(f"date -s '{set_time}'")
        output(f"[OK] Time set to {set_time}")
    else:
        out = device.shell("date").output
        output(out.strip())
    audit_log(f"sys date {set_time or ''}")


def cmd_uptime(args):
    """Device uptime."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("uptime").output
    output(out.strip())
    audit_log("sys uptime")


def cmd_thermal(args):
    """Device temperature info."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("dumpsys thermalservice | grep 'mTemp\\|Temperature' | head -10").output
    if out.strip():
        output(out.strip())
    else:
        # Fallback: battery temperature
        bat = device.shell("dumpsys battery | grep temperature").output
        if bat.strip():
            temp_match = re.search(r'temperature:\s*(\d+)', bat)
            if temp_match:
                temp = int(temp_match.group(1)) / 10
                output(f"Battery temperature: {temp}°C")
            else:
                output(bat.strip())
        else:
            output("Temperature info not available")
    audit_log("sys thermal")
