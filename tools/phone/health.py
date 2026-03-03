"""Connection health check and self-healing: status, reconnect, agent check."""

import re
import time
import subprocess

from .connection import get_device, adb_shell, adb_command, reset_connection, _run_adb
from .utils import output, error, ok, warn, audit_log
from . import config as cfg

# Health check cache
_last_health = None
_last_health_time = 0
_CACHE_TTL = 30  # seconds


def _check_adb():
    """Check ADB connection status."""
    out, rc = _run_adb("devices")
    if rc != 0:
        return False, "adb not responding"
    lines = out.strip().split("\n")[1:]
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return True, parts[0]
    return False, "no device connected"


def _check_u2_agent(device):
    """Check if u2 ATX Agent is running."""
    try:
        info = device.info
        if info and "displayWidth" in info:
            return True, "running"
    except Exception as e:
        return False, str(e)
    return False, "no response"


def _check_a11y(device):
    """Check accessibility service status."""
    try:
        out = device.shell("settings get secure enabled_accessibility_services").output.strip()
        if "uiautomator" in out.lower() or "atx" in out.lower():
            return True, out
        return False, out or "(none)"
    except Exception as e:
        return False, str(e)


def _check_screen(device):
    """Check screen state."""
    try:
        is_on = device.info.get("screenOn", False)
        return is_on, "on" if is_on else "off"
    except Exception:
        return False, "unknown"


def _check_ime(device):
    """Check current IME."""
    try:
        out = device.shell("settings get secure default_input_method").output.strip()
        is_fast = "FastInputIME" in out
        return is_fast, out
    except Exception:
        return False, "unknown"


def _check_wifi_latency(device):
    """Check WiFi ADB latency."""
    try:
        start = time.time()
        device.shell("echo ping")
        latency = (time.time() - start) * 1000
        return latency < 500, f"{latency:.0f}ms"
    except Exception:
        return False, "timeout"


def cmd_status(args):
    """Comprehensive health check."""
    global _last_health, _last_health_time

    # Check cache
    now = time.time()
    if _last_health and (now - _last_health_time) < _CACHE_TTL and not getattr(args, "force", False):
        output("[Cached health check result]")
        for line in _last_health:
            output(line)
        return

    results = []

    # 1. ADB connection
    adb_ok, adb_detail = _check_adb()
    status = "✓" if adb_ok else "✗"
    results.append(f"{status} ADB: {adb_detail}")

    if not adb_ok:
        results.append("  → Run: adb devices / adb connect <ip>:5555")
        _last_health = results
        _last_health_time = now
        for line in results:
            output(line)
        return

    # 2. u2 Agent
    try:
        device = get_device(getattr(args, "device", None))
    except SystemExit:
        results.append("✗ u2 Agent: connection failed")
        results.append("  → Run: python -m uiautomator2 init")
        _last_health = results
        _last_health_time = now
        for line in results:
            output(line)
        return

    u2_ok, u2_detail = _check_u2_agent(device)
    status = "✓" if u2_ok else "✗"
    results.append(f"{status} u2 Agent: {u2_detail}")

    # 3. Accessibility service
    a11y_ok, a11y_detail = _check_a11y(device)
    status = "✓" if a11y_ok else "✗"
    results.append(f"{status} Accessibility: {a11y_detail}")
    if not a11y_ok:
        results.append("  → Run: phone_control.py device restart-agent")

    # 4. Screen state
    screen_on, screen_detail = _check_screen(device)
    status = "✓" if screen_on else "○"
    results.append(f"{status} Screen: {screen_detail}")

    # 5. IME
    ime_ok, ime_detail = _check_ime(device)
    status = "✓" if ime_ok else "○"
    results.append(f"{status} IME: {ime_detail}")
    if not ime_ok:
        results.append("  → For text input, run: phone_control.py device ime-setup")

    # 6. Latency
    lat_ok, lat_detail = _check_wifi_latency(device)
    status = "✓" if lat_ok else "!"
    results.append(f"{status} Latency: {lat_detail}")

    # 7. Battery
    try:
        bat_out = device.shell("dumpsys battery | grep level").output
        level = re.search(r'level:\s*(\d+)', bat_out)
        bat_str = f"{level.group(1)}%" if level else "N/A"
        results.append(f"○ Battery: {bat_str}")
    except Exception:
        results.append("○ Battery: N/A")

    _last_health = results
    _last_health_time = now

    for line in results:
        output(line)
    audit_log("health status")


def cmd_reconnect(args):
    """Force reconnect to device."""
    reset_connection()
    conf = cfg.load_config()
    wifi_ip = conf.get("wifi_ip", "")
    port = conf.get("wifi_port", 5555)
    retries = conf.get("timeouts", {}).get("reconnect_retries", 3)
    interval = conf.get("timeouts", {}).get("reconnect_interval", 5)

    for attempt in range(1, retries + 1):
        output(f"[Attempt {attempt}/{retries}]")

        if wifi_ip:
            addr = f"{wifi_ip}:{port}"
            out, rc = _run_adb("connect", addr)
            if rc == 0 and "connected" in out.lower():
                ok(f"Reconnected to {addr}")
                audit_log(f"reconnect -> {addr}")
                return

        # Try to get device anyway
        try:
            device = get_device()
            device.info  # Quick test
            ok("Reconnected")
            audit_log("reconnect -> ok")
            return
        except Exception:
            pass

        if attempt < retries:
            output(f"  Retrying in {interval}s...")
            time.sleep(interval)

    error(f"Failed to reconnect after {retries} attempts")


def cmd_agent_check(args):
    """Check and auto-restart u2 agent if needed."""
    try:
        device = get_device(getattr(args, "device", None))
    except SystemExit:
        output("[FAIL] Cannot connect to device")
        return

    u2_ok, _ = _check_u2_agent(device)
    if u2_ok:
        ok("u2 Agent is healthy")
    else:
        output("[WARN] u2 Agent not responding, restarting...")
        try:
            device.shell("am force-stop com.github.uiautomator")
            time.sleep(0.5)
            device.shell("am start -n com.github.uiautomator/.MainActivity")
            time.sleep(2)
            u2_ok2, _ = _check_u2_agent(device)
            if u2_ok2:
                ok("u2 Agent restarted successfully")
            else:
                error("u2 Agent restart failed. Run 'python -m uiautomator2 init' manually.")
        except Exception as e:
            error(f"Agent restart error: {e}")
    audit_log("agent-check")
