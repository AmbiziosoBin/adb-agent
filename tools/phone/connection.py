"""Device connection management: auto-detect, singleton, reconnect."""

import subprocess
import uiautomator2 as u2

from . import config as cfg
from .utils import error, warn, retry

_device_instance = None


def _run_adb(*args):
    """Run an adb command and return stdout."""
    try:
        result = subprocess.run(
            ["adb"] + list(args),
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip(), result.returncode
    except FileNotFoundError:
        error("adb not found. Install Android Platform Tools first.")
    except subprocess.TimeoutExpired:
        return "", 1


def _detect_usb_device():
    """Detect USB-connected device serial."""
    out, rc = _run_adb("devices")
    if rc != 0:
        return None
    lines = out.strip().split("\n")[1:]  # Skip header
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serial = parts[0]
            if ":" not in serial:  # USB device (no IP:port)
                return serial
    return None


def _detect_wifi_device():
    """Detect WiFi-connected device."""
    out, rc = _run_adb("devices")
    if rc != 0:
        return None
    lines = out.strip().split("\n")[1:]
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serial = parts[0]
            if ":" in serial:  # WiFi device (IP:port)
                return serial
    return None


def _connect_wifi(ip, port=5555):
    """Connect to device via WiFi ADB."""
    addr = f"{ip}:{port}"
    out, rc = _run_adb("connect", addr)
    if rc == 0 and "connected" in out.lower():
        return addr
    return None


@retry(max_attempts=3, delay=2.0)
def get_device(device_serial=None):
    """
    Get a uiautomator2 device instance (singleton).

    Priority:
    1. Explicit device_serial parameter
    2. Config file device setting
    3. Auto-detect USB
    4. Auto-detect WiFi
    """
    global _device_instance

    if _device_instance is not None and device_serial is None:
        try:
            _device_instance.info  # Quick health check
            return _device_instance
        except Exception:
            _device_instance = None  # Stale connection

    conf = cfg.load_config()
    serial = device_serial or conf.get("device", "")

    if not serial:
        # Auto-detect
        serial = _detect_usb_device()
        if not serial:
            # Try WiFi
            wifi_ip = conf.get("wifi_ip", "")
            if wifi_ip:
                serial = _connect_wifi(wifi_ip, conf.get("wifi_port", 5555))
            if not serial:
                serial = _detect_wifi_device()
        if not serial:
            error("No device found. Connect via USB or configure WiFi ADB in config.yaml")

    try:
        d = u2.connect(serial)
        d.settings["wait_timeout"] = cfg.get_timeout("input_action")
        _device_instance = d
        return d
    except Exception as e:
        error(f"Failed to connect to device '{serial}': {e}")


def reset_connection():
    """Force reset the cached connection."""
    global _device_instance
    _device_instance = None


def adb_shell(command, device_serial=None):
    """Run an adb shell command directly and return stdout.
    Uses shell=True to support pipes and redirects in the command string.
    """
    conf = cfg.load_config()
    serial = device_serial or conf.get("device", "")
    serial_args = f"-s {serial} " if serial else ""
    cmd_str = f"adb {serial_args}shell {command}"
    try:
        result = subprocess.run(
            cmd_str, shell=True,
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip(), result.returncode
    except FileNotFoundError:
        error("adb not found. Install Android Platform Tools first.")
    except subprocess.TimeoutExpired:
        return "", 1


def adb_command(*args, device_serial=None):
    """Run an adb command (non-shell) and return stdout."""
    conf = cfg.load_config()
    serial = device_serial or conf.get("device", "")
    cmd_args = []
    if serial:
        cmd_args = ["-s", serial]
    cmd_args.extend(args)
    out, rc = _run_adb(*cmd_args)
    return out, rc
