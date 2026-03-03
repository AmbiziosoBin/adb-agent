"""Device control: screen, lock/unlock, volume, brightness, connectivity, etc."""

import re
import time

from .connection import get_device, adb_shell, adb_command
from .utils import output, error, ok, audit_log
from . import config as cfg


def cmd_info(args):
    """Device comprehensive info."""
    device = get_device(getattr(args, "device", None))
    info = device.info
    dev_info = device.device_info

    output(f'model: {dev_info.get("model", "N/A")}')
    output(f'brand: {dev_info.get("brand", "N/A")}')
    output(f'serial: {dev_info.get("serial", "N/A")}')
    output(f'android: {dev_info.get("version", "N/A")}')
    output(f'sdk: {dev_info.get("sdk", "N/A")}')
    output(f'resolution: {info.get("displayWidth", 0)}x{info.get("displayHeight", 0)}')
    output(f'screen: {"on" if info.get("screenOn") else "off"}')

    # Battery
    bat_out = device.shell("dumpsys battery").output
    level = re.search(r'level:\s*(\d+)', bat_out)
    status = re.search(r'status:\s*(\d+)', bat_out)
    status_map = {"1": "unknown", "2": "charging", "3": "discharging", "4": "not charging", "5": "full"}
    bat_level = level.group(1) if level else "N/A"
    bat_status = status_map.get(status.group(1), "unknown") if status else "N/A"
    output(f'battery: {bat_level}% ({bat_status})')

    # IP
    ip_out = device.shell("ip route | grep wlan0 | grep src").output
    ip_match = re.search(r'src\s+([\d.]+)', ip_out)
    output(f'ip: {ip_match.group(1) if ip_match else "N/A"}')
    audit_log("device info")


def cmd_screen_on(args):
    """Wake up screen."""
    device = get_device(getattr(args, "device", None))
    if not device.info.get("screenOn"):
        device.press("power")
        time.sleep(0.3)
    audit_log("device screen-on")
    ok("Screen on")


def cmd_screen_off(args):
    """Turn off screen."""
    device = get_device(getattr(args, "device", None))
    if device.info.get("screenOn"):
        device.press("power")
        time.sleep(0.3)
    audit_log("device screen-off")
    ok("Screen off")


def cmd_is_screen_on(args):
    """Check screen state."""
    device = get_device(getattr(args, "device", None))
    is_on = device.info.get("screenOn", False)
    output("true" if is_on else "false")


def cmd_unlock(args):
    """Unlock screen."""
    device = get_device(getattr(args, "device", None))

    # Wake up first
    if not device.info.get("screenOn"):
        device.press("power")
        time.sleep(0.5)

    w, h = cfg.get_screen_size()

    if getattr(args, "swipe", False):
        device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
        time.sleep(0.3)
        audit_log("device unlock --swipe")
        ok("Swipe unlock done")
    elif getattr(args, "pin", None):
        # Swipe up first to reach PIN screen
        device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
        time.sleep(0.3)
        for digit in args.pin:
            device(text=digit).click()
            time.sleep(0.08)
        # Some devices need Enter after PIN
        time.sleep(0.2)
        audit_log("device unlock --pin ****")
        ok("PIN unlock done")
    elif getattr(args, "password", None):
        device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
        time.sleep(0.3)
        device.send_keys(args.password)
        device.press("enter")
        time.sleep(0.3)
        audit_log("device unlock --password ****")
        ok("Password unlock done")
    elif getattr(args, "pattern", None):
        # Pattern: comma-separated coordinates "x1,y1,x2,y2,x3,y3..."
        device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
        time.sleep(0.3)
        coords = args.pattern.split(",")
        points = [(int(coords[i]), int(coords[i + 1])) for i in range(0, len(coords), 2)]
        device.swipe_points(points, duration=0.5)
        time.sleep(0.3)
        audit_log("device unlock --pattern")
        ok("Pattern unlock done")
    else:
        # Default: swipe up
        device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
        time.sleep(0.3)
        audit_log("device unlock")
        ok("Swipe unlock done (default)")


def cmd_lock(args):
    """Lock screen."""
    device = get_device(getattr(args, "device", None))
    if device.info.get("screenOn"):
        device.press("power")
    audit_log("device lock")
    ok("Screen locked")


def cmd_rotate(args):
    """Rotate screen."""
    device = get_device(getattr(args, "device", None))
    rotation = args.rotation  # auto, 0, 90, 180, 270

    if rotation == "auto":
        device.shell("settings put system accelerometer_rotation 1")
        ok("Auto-rotation enabled")
    else:
        device.shell("settings put system accelerometer_rotation 0")
        rot_map = {"0": "0", "90": "1", "180": "2", "270": "3"}
        val = rot_map.get(rotation, "0")
        device.shell(f"settings put system user_rotation {val}")
        ok(f"Rotation set to {rotation}°")
    audit_log(f"device rotate {rotation}")


def cmd_brightness(args):
    """Set screen brightness."""
    device = get_device(getattr(args, "device", None))
    value = args.value

    if value == "auto":
        device.shell("settings put system screen_brightness_mode 1")
        ok("Auto brightness enabled")
    else:
        val = int(value)
        if not 0 <= val <= 255:
            error("Brightness must be 0-255 or 'auto'")
        device.shell("settings put system screen_brightness_mode 0")
        device.shell(f"settings put system screen_brightness {val}")
        ok(f"Brightness set to {val}")
    audit_log(f"device brightness {value}")


def cmd_volume(args):
    """Volume control."""
    device = get_device(getattr(args, "device", None))
    stream = args.stream  # media, ring, alarm, notification
    action = args.action  # up, down, set, mute
    value = getattr(args, "value", None)

    stream_map = {"media": "3", "ring": "2", "alarm": "4", "notification": "5"}
    stream_id = stream_map.get(stream, "3")

    if action == "up":
        device.press("volume_up")
        ok(f"{stream} volume up")
    elif action == "down":
        device.press("volume_down")
        ok(f"{stream} volume down")
    elif action == "set" and value is not None:
        device.shell(f"media volume --stream {stream_id} --set {value}")
        ok(f"{stream} volume set to {value}")
    elif action == "mute":
        device.shell(f"media volume --stream {stream_id} --set 0")
        ok(f"{stream} muted")
    else:
        error("Usage: device volume <stream> <up|down|set|mute> [value]")
    audit_log(f"device volume {stream} {action} {value or ''}")


def cmd_wifi(args):
    """WiFi control."""
    device = get_device(getattr(args, "device", None))
    action = args.action  # on, off, status, connect

    if action == "on":
        device.shell("svc wifi enable")
        ok("WiFi enabled")
    elif action == "off":
        device.shell("svc wifi disable")
        ok("WiFi disabled")
    elif action == "status":
        out = device.shell("dumpsys wifi | grep 'Wi-Fi is'").output
        ssid_out = device.shell("dumpsys wifi | grep 'mWifiInfo'").output
        output(out.strip())
        ssid_match = re.search(r'SSID:\s*"?([^",]+)', ssid_out)
        if ssid_match:
            output(f"SSID: {ssid_match.group(1)}")
    elif action == "connect":
        ssid = getattr(args, "ssid", None)
        password = getattr(args, "wifi_password", None)
        if not ssid:
            error("SSID required for WiFi connect")
        cmd = f'cmd wifi connect-network "{ssid}" wpa2 "{password}"' if password else f'cmd wifi connect-network "{ssid}" open'
        device.shell(cmd)
        ok(f"Connecting to {ssid}")
    audit_log(f"device wifi {action}")


def cmd_bluetooth(args):
    """Bluetooth control."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("svc bluetooth enable")
        ok("Bluetooth enabled")
    elif action == "off":
        device.shell("svc bluetooth disable")
        ok("Bluetooth disabled")
    elif action == "status":
        out = device.shell("dumpsys bluetooth_manager | grep 'state:'").output
        output(out.strip() or "Bluetooth status unknown")
    audit_log(f"device bluetooth {action}")


def cmd_airplane(args):
    """Airplane mode control."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("settings put global airplane_mode_on 1")
        device.shell("am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true")
        ok("Airplane mode on")
    elif action == "off":
        device.shell("settings put global airplane_mode_on 0")
        device.shell("am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false")
        ok("Airplane mode off")
    elif action == "status":
        out = device.shell("settings get global airplane_mode_on").output.strip()
        output("on" if out == "1" else "off")
    audit_log(f"device airplane {action}")


def cmd_mobile_data(args):
    """Mobile data control."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("svc data enable")
        ok("Mobile data enabled")
    elif action == "off":
        device.shell("svc data disable")
        ok("Mobile data disabled")
    elif action == "status":
        out = device.shell("settings get global mobile_data").output.strip()
        output("on" if out == "1" else "off")
    audit_log(f"device mobile-data {action}")


def cmd_hotspot(args):
    """Hotspot control."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("am start -n com.android.settings/.TetherSettings")
        ok("Opened hotspot settings (manual toggle may be needed)")
    elif action == "off":
        device.shell("am start -n com.android.settings/.TetherSettings")
        ok("Opened hotspot settings (manual toggle may be needed)")
    audit_log(f"device hotspot {action}")


def cmd_battery(args):
    """Detailed battery info."""
    device = get_device(getattr(args, "device", None))
    bat_out = device.shell("dumpsys battery").output

    for line in bat_out.strip().split("\n"):
        line = line.strip()
        if any(k in line.lower() for k in ["level", "status", "health", "temperature", "voltage", "plugged", "charging"]):
            output(line)
    audit_log("device battery")


def cmd_reboot(args):
    """Reboot device (requires --confirm)."""
    if not getattr(args, "confirm", False):
        error("Reboot requires --confirm flag for safety")

    device = get_device(getattr(args, "device", None))
    mode = ""
    if getattr(args, "recovery", False):
        mode = "recovery"
    elif getattr(args, "bootloader", False):
        mode = "bootloader"

    if mode:
        device.shell(f"reboot {mode}")
        ok(f"Rebooting to {mode}")
    else:
        device.shell("reboot")
        ok("Rebooting")
    audit_log(f"device reboot {mode}")


def cmd_dnd(args):
    """Do not disturb mode."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("cmd notification set_dnd on")
        ok("DND enabled")
    elif action == "off":
        device.shell("cmd notification set_dnd off")
        ok("DND disabled")
    audit_log(f"device dnd {action}")


def cmd_nfc(args):
    """NFC control."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("svc nfc enable")
        ok("NFC enabled")
    elif action == "off":
        device.shell("svc nfc disable")
        ok("NFC disabled")
    elif action == "status":
        out = device.shell("dumpsys nfc | grep 'mState='").output
        output(out.strip() or "NFC status unknown")
    audit_log(f"device nfc {action}")


def cmd_gps(args):
    """GPS control."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("settings put secure location_mode 3")
        ok("GPS enabled (high accuracy)")
    elif action == "off":
        device.shell("settings put secure location_mode 0")
        ok("GPS disabled")
    elif action == "status":
        out = device.shell("settings get secure location_mode").output.strip()
        mode_map = {"0": "off", "1": "sensors only", "2": "battery saving", "3": "high accuracy"}
        output(f"GPS: {mode_map.get(out, out)}")
    audit_log(f"device gps {action}")


def cmd_ime(args):
    """Input method management."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "list":
        out = device.shell("ime list -s").output
        for line in out.strip().split("\n"):
            if line.strip():
                output(line.strip())
    elif action == "current":
        out = device.shell("settings get secure default_input_method").output
        output(out.strip())
    elif action == "set":
        ime_id = getattr(args, "ime_id", None)
        if not ime_id:
            error("IME id required. Run 'device ime list' to see available IMEs.")
        device.shell(f"ime set {ime_id}")
        ok(f"IME set to {ime_id}")
    audit_log(f"device ime {action}")


def cmd_stay_awake(args):
    """Stay awake (don't sleep while charging)."""
    device = get_device(getattr(args, "device", None))
    action = args.action

    if action == "on":
        device.shell("settings put global stay_on_while_plugged_in 7")
        ok("Stay awake enabled")
    elif action == "off":
        device.shell("settings put global stay_on_while_plugged_in 0")
        ok("Stay awake disabled")
    audit_log(f"device stay-awake {action}")


def cmd_check_a11y(args):
    """Check ATX Agent accessibility service status."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("settings get secure enabled_accessibility_services").output
    services = out.strip()
    if "uiautomator" in services.lower() or "atx" in services.lower():
        ok(f"Accessibility service active: {services}")
    else:
        output(f"[WARN] ATX accessibility service may not be active. Current: {services}")
        output("Run 'device restart-agent' to fix.")
    audit_log("device check-a11y")


def cmd_restart_agent(args):
    """Restart u2 ATX Agent."""
    device = get_device(getattr(args, "device", None))
    try:
        device.shell("am force-stop com.github.uiautomator")
        time.sleep(0.5)
        device.shell("am start -n com.github.uiautomator/.MainActivity")
        time.sleep(1.5)
        # Verify
        out = device.shell("settings get secure enabled_accessibility_services").output
        ok(f"Agent restarted. A11y services: {out.strip()}")
    except Exception as e:
        error(f"Failed to restart agent: {e}")
    audit_log("device restart-agent")


def cmd_ime_setup(args):
    """Setup u2 FastInputIME as default."""
    device = get_device(getattr(args, "device", None))
    # Save current IME
    current = device.shell("settings get secure default_input_method").output.strip()
    output(f"Current IME: {current}")

    # Set FastInputIME
    device.shell("ime enable com.github.uiautomator/.FastInputIME")
    device.shell("ime set com.github.uiautomator/.FastInputIME")
    ok("FastInputIME set as default")
    output(f"Previous IME saved: {current}")
    audit_log(f"device ime-setup (was: {current})")


def cmd_ime_restore(args):
    """Restore original IME."""
    device = get_device(getattr(args, "device", None))
    ime_id = getattr(args, "ime_id", None)
    if not ime_id:
        # List available IMEs and pick the first non-FastInputIME
        out = device.shell("ime list -s").output
        imes = [line.strip() for line in out.strip().split("\n")
                if line.strip() and "FastInput" not in line]
        if imes:
            ime_id = imes[0]
            output(f"No IME specified, using first available: {ime_id}")
        else:
            error("No suitable IME found. Run 'device ime list' to see available IMEs.")

    device.shell(f"ime set {ime_id}")
    ok(f"IME restored to {ime_id}")
    audit_log(f"device ime-restore {ime_id}")
