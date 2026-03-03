#!/usr/bin/env python3
"""
phone_control.py — Unified CLI entry point for Android phone control.
Usage: python3 phone_control.py <command> <subcommand> [options]
"""

import sys
import os
import argparse

# Add tools directory to path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "tools")
sys.path.insert(0, _TOOLS_DIR)

from phone import config as cfg
from phone import utils


def build_parser():
    parser = argparse.ArgumentParser(
        prog="phone_control.py",
        description="Control Android phone via ADB + uiautomator2",
    )
    parser.add_argument("--device", "-d", default=None, help="Device serial or IP:port")
    parser.add_argument("--json", action="store_true", help="(default, kept for backward compat)")
    parser.add_argument("--plain", action="store_true", help="Force plain text output instead of JSON")
    sub = parser.add_subparsers(dest="command", help="Command category")

    # ─── UI ───
    ui = sub.add_parser("ui", help="UI tree operations")
    ui_sub = ui.add_subparsers(dest="ui_cmd")

    # ui dump
    dump = ui_sub.add_parser("dump", help="Dump UI hierarchy")
    dump.add_argument("--interactive", action="store_true", help="Only interactive elements")
    dump.add_argument("--text", action="store_true", help="Only elements with text")
    dump.add_argument("--numbered", action="store_true", help="Number interactive elements")
    dump.add_argument("--package", type=str, help="Filter by package name")
    dump.add_argument("--depth", type=int, help="Max tree depth")
    dump.add_argument("--search", type=str, help="Search keyword")
    dump.add_argument("--rect", type=str, help="Region filter: x1,y1,x2,y2")
    dump.add_argument("--timeout", type=float, help="Dump timeout in seconds")

    # ui find
    find = ui_sub.add_parser("find", help="Find element by selector")
    find.add_argument("selector_type", choices=["text", "id", "class", "desc"])
    find.add_argument("value", type=str)

    # ui exists
    exists = ui_sub.add_parser("exists", help="Check element existence")
    exists.add_argument("selector_type", choices=["text", "id"])
    exists.add_argument("value", type=str)

    # ui current
    ui_sub.add_parser("current", help="Current activity + package (lightweight)")

    # ui watch
    watch = ui_sub.add_parser("watch", help="Watch UI changes")
    watch.add_argument("--duration", type=int, default=10, help="Watch duration in seconds")

    # ui diff
    ui_sub.add_parser("diff", help="Diff against last dump")

    # ─── INPUT ───
    inp = sub.add_parser("input", help="Input control")
    inp_sub = inp.add_subparsers(dest="input_cmd")

    # input tap
    tap = inp_sub.add_parser("tap", help="Tap coordinates")
    tap.add_argument("x", type=str)
    tap.add_argument("y", type=str)

    # input tap-text
    tap_text = inp_sub.add_parser("tap-text", help="Tap by text")
    tap_text.add_argument("text", type=str)
    tap_text.add_argument("--index", type=int, default=1, help="Which match to tap (1=first, 2=second, etc.)")

    # input tap-id
    tap_id = inp_sub.add_parser("tap-id", help="Tap by resource-id")
    tap_id.add_argument("resource_id", type=str)

    # input tap-desc
    tap_desc = inp_sub.add_parser("tap-desc", help="Tap by content-desc")
    tap_desc.add_argument("desc", type=str)

    # input tap-nth
    tap_nth = inp_sub.add_parser("tap-nth", help="Tap Nth interactive element")
    tap_nth.add_argument("n", type=str)

    # input long-tap
    ltap = inp_sub.add_parser("long-tap", help="Long press")
    ltap.add_argument("x", type=str)
    ltap.add_argument("y", type=str)
    ltap.add_argument("--duration", type=float, default=1.0)

    # input double-tap
    dtap = inp_sub.add_parser("double-tap", help="Double tap")
    dtap.add_argument("x", type=str)
    dtap.add_argument("y", type=str)

    # input swipe
    swipe = inp_sub.add_parser("swipe", help="Swipe coordinates")
    swipe.add_argument("x1", type=str)
    swipe.add_argument("y1", type=str)
    swipe.add_argument("x2", type=str)
    swipe.add_argument("y2", type=str)
    swipe.add_argument("duration_pos", nargs="?", default=None, help=argparse.SUPPRESS)
    swipe.add_argument("--duration", type=float, default=None)

    # input swipe-dir
    swipe_dir = inp_sub.add_parser("swipe-dir", help="Swipe direction")
    swipe_dir.add_argument("direction", choices=["up", "down", "left", "right"])
    swipe_dir.add_argument("--distance", type=float, default=0.5)

    # input scroll-to
    scroll = inp_sub.add_parser("scroll-to", help="Scroll until text found")
    scroll.add_argument("text", type=str)
    scroll.add_argument("--max-scrolls", type=int, default=10)

    # input text
    text_inp = inp_sub.add_parser("text", help="Type text")
    text_inp.add_argument("content", type=str)

    # input set-text
    set_text = inp_sub.add_parser("set-text", help="Set text on input field")
    set_text.add_argument("selector", type=str)
    set_text.add_argument("content", type=str)

    # input clear
    clear = inp_sub.add_parser("clear", help="Clear input field")
    clear.add_argument("selector", nargs="?", default=None)

    # input key
    key = inp_sub.add_parser("key", help="Send key event")
    key.add_argument("keycode", type=str)

    # input pinch
    pinch = inp_sub.add_parser("pinch", help="Pinch gesture")
    pinch.add_argument("direction", choices=["in", "out"])
    pinch.add_argument("--scale", type=float, default=0.5)

    # input drag
    drag = inp_sub.add_parser("drag", help="Drag")
    drag.add_argument("x1", type=str)
    drag.add_argument("y1", type=str)
    drag.add_argument("x2", type=str)
    drag.add_argument("y2", type=str)
    drag.add_argument("--duration", type=float, default=None)

    # input multi-tap
    mtap = inp_sub.add_parser("multi-tap", help="Multi-point tap")
    mtap.add_argument("points", nargs="+", help="x1,y1 x2,y2 ...")

    # input gesture
    gesture = inp_sub.add_parser("gesture", help="Custom gesture path")
    gesture.add_argument("coords", nargs="+", help="x1,y1 x2,y2 x3,y3 ...")
    gesture.add_argument("--duration", type=float, default=0.5)

    # input captcha-swipe
    cswipe = inp_sub.add_parser("captcha-swipe", help="Human-like CAPTCHA slider swipe")
    cswipe.add_argument("x1", type=str, help="Slider start X")
    cswipe.add_argument("y1", type=str, help="Slider start Y")
    cswipe.add_argument("x2", type=str, help="Target end X")
    cswipe.add_argument("y2", type=str, help="Target end Y")
    cswipe.add_argument("--duration", type=float, default=0.8, help="Movement duration (seconds)")
    cswipe.add_argument("--hold-start", type=float, default=0.12, dest="hold_start", help="Hold at start before moving (seconds)")
    cswipe.add_argument("--hold-end", type=float, default=0.08, dest="hold_end", help="Hold at end before releasing (seconds)")
    cswipe.add_argument("--easing", type=str, default="human", choices=["linear", "ease-in", "ease-out", "ease-in-out", "human"], help="Speed curve profile")
    cswipe.add_argument("--overshoot", type=int, default=0, help="Pixels to overshoot past target then settle back")
    cswipe.add_argument("--y-wobble", type=int, default=0, dest="y_wobble", help="Max vertical deviation in pixels")
    cswipe.add_argument("--steps", type=int, default=30, help="Number of intermediate points (more=smoother)")
    cswipe.add_argument("--verify", action="store_true", help="Check if CAPTCHA passed after swipe")
    cswipe.add_argument("--wait-after", type=float, default=1.5, dest="wait_after", help="Seconds to wait before verification")

    # ─── DEVICE ───
    dev = sub.add_parser("device", help="Device control")
    dev_sub = dev.add_subparsers(dest="device_cmd")

    dev_sub.add_parser("info", help="Device info")
    dev_sub.add_parser("screen-on", help="Wake screen")
    dev_sub.add_parser("screen-off", help="Sleep screen")
    dev_sub.add_parser("is-screen-on", help="Check screen state")

    unlock = dev_sub.add_parser("unlock", help="Unlock screen")
    unlock.add_argument("--pin", type=str)
    unlock.add_argument("--password", type=str)
    unlock.add_argument("--pattern", type=str)
    unlock.add_argument("--swipe", action="store_true")

    dev_sub.add_parser("lock", help="Lock screen")

    rotate = dev_sub.add_parser("rotate", help="Rotate screen")
    rotate.add_argument("rotation", choices=["auto", "0", "90", "180", "270"])

    brightness = dev_sub.add_parser("brightness", help="Set brightness")
    brightness.add_argument("value", type=str, help="0-255 or 'auto'")

    volume = dev_sub.add_parser("volume", help="Volume control")
    volume.add_argument("stream", choices=["media", "ring", "alarm", "notification"])
    volume.add_argument("action", choices=["up", "down", "set", "mute"])
    volume.add_argument("value", nargs="?", default=None)

    wifi = dev_sub.add_parser("wifi", help="WiFi control")
    wifi.add_argument("action", choices=["on", "off", "status", "connect"])
    wifi.add_argument("ssid", nargs="?", default=None)
    wifi.add_argument("--wifi-password", type=str)

    bt = dev_sub.add_parser("bluetooth", help="Bluetooth control")
    bt.add_argument("action", choices=["on", "off", "status"])

    airplane = dev_sub.add_parser("airplane", help="Airplane mode")
    airplane.add_argument("action", choices=["on", "off", "status"])

    mdata = dev_sub.add_parser("mobile-data", help="Mobile data")
    mdata.add_argument("action", choices=["on", "off", "status"])

    hotspot = dev_sub.add_parser("hotspot", help="Hotspot")
    hotspot.add_argument("action", choices=["on", "off"])

    dev_sub.add_parser("battery", help="Battery info")

    reboot = dev_sub.add_parser("reboot", help="Reboot device")
    reboot.add_argument("--confirm", action="store_true", required=True)
    reboot.add_argument("--recovery", action="store_true")
    reboot.add_argument("--bootloader", action="store_true")

    dnd = dev_sub.add_parser("dnd", help="Do not disturb")
    dnd.add_argument("action", choices=["on", "off"])

    nfc = dev_sub.add_parser("nfc", help="NFC control")
    nfc.add_argument("action", choices=["on", "off", "status"])

    gps = dev_sub.add_parser("gps", help="GPS control")
    gps.add_argument("action", choices=["on", "off", "status"])

    ime = dev_sub.add_parser("ime", help="IME management")
    ime.add_argument("action", choices=["list", "current", "set"])
    ime.add_argument("ime_id", nargs="?", default=None)

    stay = dev_sub.add_parser("stay-awake", help="Stay awake")
    stay.add_argument("action", choices=["on", "off"])

    dev_sub.add_parser("check-a11y", help="Check accessibility service")
    dev_sub.add_parser("restart-agent", help="Restart u2 ATX Agent")
    dev_sub.add_parser("ime-setup", help="Setup FastInputIME")

    ime_restore = dev_sub.add_parser("ime-restore", help="Restore original IME")
    ime_restore.add_argument("ime_id", nargs="?", default=None)

    # ─── APP ───
    app = sub.add_parser("app", help="Application management")
    app_sub = app.add_subparsers(dest="app_cmd")

    app_list = app_sub.add_parser("list", help="List apps")
    app_list.add_argument("--third-party", action="store_true")
    app_list.add_argument("--system", action="store_true")
    app_list.add_argument("--search", type=str)

    app_info = app_sub.add_parser("info", help="App info")
    app_info.add_argument("package", type=str)

    app_launch = app_sub.add_parser("launch", help="Launch app")
    app_launch.add_argument("package", type=str)
    app_launch.add_argument("--activity", type=str)

    app_stop = app_sub.add_parser("stop", help="Stop app")
    app_stop.add_argument("package", type=str)

    app_sub.add_parser("stop-all", help="Stop all third-party apps")

    app_install = app_sub.add_parser("install", help="Install APK")
    app_install.add_argument("source", type=str, help="Local path or URL")

    app_uninstall = app_sub.add_parser("uninstall", help="Uninstall app")
    app_uninstall.add_argument("package", type=str)
    app_uninstall.add_argument("--confirm", action="store_true", required=True)
    app_uninstall.add_argument("--keep-data", action="store_true")

    app_clear = app_sub.add_parser("clear", help="Clear app data")
    app_clear.add_argument("package", type=str)
    app_clear.add_argument("--confirm", action="store_true", required=True)

    app_sub.add_parser("current", help="Current foreground app")
    app_sub.add_parser("recent", help="Recent apps")

    app_perm = app_sub.add_parser("permissions", help="App permissions")
    app_perm.add_argument("package", type=str)
    app_perm.add_argument("--grant", type=str)
    app_perm.add_argument("--revoke", type=str)

    app_sub.add_parser("running", help="Running apps")

    app_size = app_sub.add_parser("size", help="App storage size")
    app_size.add_argument("package", type=str)

    app_dis = app_sub.add_parser("disable", help="Disable app")
    app_dis.add_argument("package", type=str)

    app_en = app_sub.add_parser("enable", help="Enable app")
    app_en.add_argument("package", type=str)

    # ─── FILE ───
    f = sub.add_parser("file", help="File management")
    f_sub = f.add_subparsers(dest="file_cmd")

    push = f_sub.add_parser("push", help="Push file to phone")
    push.add_argument("local_path", type=str)
    push.add_argument("remote_path", type=str)

    pull = f_sub.add_parser("pull", help="Pull file from phone")
    pull.add_argument("remote_path", type=str)
    pull.add_argument("local_path", nargs="?", default=None)

    ls = f_sub.add_parser("ls", help="List directory")
    ls.add_argument("remote_path", type=str)
    ls.add_argument("--detail", action="store_true")

    rm = f_sub.add_parser("rm", help="Delete file")
    rm.add_argument("remote_path", type=str)
    rm.add_argument("--confirm", action="store_true", required=True)

    mkdir = f_sub.add_parser("mkdir", help="Create directory")
    mkdir.add_argument("remote_path", type=str)

    cat = f_sub.add_parser("cat", help="View file")
    cat.add_argument("remote_path", type=str)

    stat = f_sub.add_parser("stat", help="File info")
    stat.add_argument("remote_path", type=str)

    # ─── SCREENSHOT ───
    ss = sub.add_parser("screenshot", help="Take screenshot")
    ss.add_argument("--filename", type=str)
    ss.add_argument("--quality", type=int, default=80)
    ss.add_argument("--element", type=str)

    # ─── SCREENRECORD ───
    sr = sub.add_parser("screenrecord", help="Screen recording")
    sr_sub = sr.add_subparsers(dest="sr_cmd")

    sr_start = sr_sub.add_parser("start", help="Start recording")
    sr_start.add_argument("--filename", type=str)
    sr_start.add_argument("--duration", type=int, default=30)

    sr_sub.add_parser("stop", help="Stop recording")

    # ─── SYS ───
    sys_p = sub.add_parser("sys", help="System info")
    sys_sub = sys_p.add_subparsers(dest="sys_cmd")

    proc = sys_sub.add_parser("processes", help="Processes")
    proc.add_argument("--top", type=int, default=10)

    sys_sub.add_parser("memory", help="Memory info")
    sys_sub.add_parser("storage", help="Storage info")
    sys_sub.add_parser("cpu", help="CPU info")
    sys_sub.add_parser("network", help="Network info")

    props = sys_sub.add_parser("props", help="System properties")
    props.add_argument("keyword", nargs="?", default=None)

    logcat = sys_sub.add_parser("logcat", help="View logs")
    logcat.add_argument("--filter", type=str)
    logcat.add_argument("--level", type=str)
    logcat.add_argument("--lines", type=int, default=20)
    logcat.add_argument("--app", type=str)

    notif = sys_sub.add_parser("notifications", help="Notifications")
    notif.add_argument("--clear", action="store_true")

    settings = sys_sub.add_parser("settings", help="System settings")
    settings.add_argument("namespace", choices=["system", "secure", "global"])
    settings.add_argument("action", choices=["get", "put"])
    settings.add_argument("key", type=str)
    settings.add_argument("value", nargs="?", default=None)

    date = sys_sub.add_parser("date", help="Date/time")
    date.add_argument("--set", type=str)

    sys_sub.add_parser("uptime", help="Uptime")
    sys_sub.add_parser("thermal", help="Temperature")

    # ─── CALL ───
    call = sub.add_parser("call", help="Phone call")
    call_sub = call.add_subparsers(dest="call_cmd")

    dial = call_sub.add_parser("dial", help="Make a call")
    dial.add_argument("number", type=str)

    call_sub.add_parser("end", help="End call")
    call_sub.add_parser("accept", help="Accept call")

    # ─── SMS ───
    sms = sub.add_parser("sms", help="SMS")
    sms_sub = sms.add_subparsers(dest="sms_cmd")

    sms_send = sms_sub.add_parser("send", help="Send SMS")
    sms_send.add_argument("number", type=str)
    sms_send.add_argument("content", type=str)

    sms_read = sms_sub.add_parser("read", help="Read SMS")
    sms_read.add_argument("--count", type=int, default=5)
    sms_read.add_argument("--from", dest="from_number", type=str)

    # ─── CONTACTS ───
    contacts = sub.add_parser("contacts", help="Contacts")
    c_sub = contacts.add_subparsers(dest="contacts_cmd")

    c_list = c_sub.add_parser("list", help="List contacts")
    c_list.add_argument("--search", type=str)

    c_add = c_sub.add_parser("add", help="Add contact")
    c_add.add_argument("name", type=str)
    c_add.add_argument("number", type=str)
    c_add.add_argument("email", nargs="?", default=None)

    c_del = c_sub.add_parser("delete", help="Delete contact")
    c_del.add_argument("query", type=str)

    # ─── MEDIA ───
    media = sub.add_parser("media", help="Media control")
    media_sub = media.add_subparsers(dest="media_cmd")

    media_sub.add_parser("play-pause", help="Toggle play/pause")
    media_sub.add_parser("next", help="Next track")
    media_sub.add_parser("prev", help="Previous track")
    media_sub.add_parser("stop", help="Stop media")

    cam = media_sub.add_parser("camera", help="Open camera")
    cam.add_argument("mode", choices=["photo", "video"])

    gal = media_sub.add_parser("gallery", help="Gallery info")
    gal.add_argument("--recent", type=int, default=5)

    rec_audio = media_sub.add_parser("record-audio", help="Audio recording")
    rec_audio_sub = rec_audio.add_subparsers(dest="rec_cmd")
    ra_start = rec_audio_sub.add_parser("start", help="Start recording")
    ra_start.add_argument("--filename", type=str)
    rec_audio_sub.add_parser("stop", help="Stop recording")

    # ─── WAIT ───
    wait_text = sub.add_parser("wait", help="Wait for condition")
    wait_sub = wait_text.add_subparsers(dest="wait_cmd")

    wt = wait_sub.add_parser("text", help="Wait for text")
    wt.add_argument("text", type=str)
    wt.add_argument("--timeout", type=float, default=10)

    wg = wait_sub.add_parser("gone", help="Wait for text to disappear")
    wg.add_argument("text", type=str)
    wg.add_argument("--timeout", type=float, default=10)

    wa = wait_sub.add_parser("activity", help="Wait for activity")
    wa.add_argument("activity", type=str)
    wa.add_argument("--timeout", type=float, default=10)

    # ─── ASSERT ───
    assert_p = sub.add_parser("assert", help="Assert condition")
    assert_sub = assert_p.add_subparsers(dest="assert_cmd")

    at = assert_sub.add_parser("text", help="Assert text exists")
    at.add_argument("text", type=str)

    ant = assert_sub.add_parser("not-text", help="Assert text not exists")
    ant.add_argument("text", type=str)

    # ─── SHELL ───
    shell = sub.add_parser("shell", help="Run adb shell command")
    shell.add_argument("command", type=str)

    # ─── INTENT ───
    intent = sub.add_parser("intent", help="Send Intent")
    intent.add_argument("action", type=str)
    intent.add_argument("--data", type=str)
    intent.add_argument("--package", type=str)
    intent.add_argument("--extra", nargs="*")

    # ─── CLIPBOARD ───
    clip = sub.add_parser("clipboard", help="Clipboard operations")
    clip_sub = clip.add_subparsers(dest="clip_cmd")
    clip_sub.add_parser("get", help="Get clipboard")
    clip_set = clip_sub.add_parser("set", help="Set clipboard")
    clip_set.add_argument("content", type=str)

    # ─── OPEN ───
    open_url = sub.add_parser("open-url", help="Open URL in browser")
    open_url.add_argument("url", type=str)

    open_settings = sub.add_parser("open-settings", help="Open system settings")
    open_settings.add_argument("page", nargs="?", default=None)

    # ─── WATCHER ───
    watcher = sub.add_parser("watcher", help="UI watcher")
    w_sub = watcher.add_subparsers(dest="watcher_cmd")

    w_add = w_sub.add_parser("add", help="Add watcher")
    w_add.add_argument("name", type=str)
    w_add.add_argument("--when", nargs=2, metavar=("TYPE", "VALUE"), dest="when_args")
    w_add.add_argument("--do", type=str, dest="do_action", choices=["click", "back", "dismiss"])

    w_remove = w_sub.add_parser("remove", help="Remove watcher")
    w_remove.add_argument("name", nargs="?", default=None)
    w_remove.add_argument("--all", action="store_true")

    w_sub.add_parser("list", help="List watchers")

    # ─── TOAST ───
    sub.add_parser("toast", help="Get recent toast")

    # ─── LOCATION ───
    loc = sub.add_parser("location", help="Location")
    loc_sub = loc.add_subparsers(dest="loc_cmd")

    mock = loc_sub.add_parser("mock", help="Mock GPS location")
    mock.add_argument("latitude", type=str)
    mock.add_argument("longitude", type=str)

    loc_sub.add_parser("mock-stop", help="Stop location mock")

    # ─── BATCH ───
    batch = sub.add_parser("batch", help="Batch execute commands from file")
    batch.add_argument("file", type=str)

    # ─── BATCH-STEPS (AI batch operations) ───
    bsteps = sub.add_parser("batch-steps", help="Execute multiple steps in one call (JSON input)")
    bsteps.add_argument("steps_json", type=str, help='JSON array of steps or path to .json file')
    bsteps.add_argument("--stop-on-error", action="store_true", default=True, help="Stop on first error (default: true)")
    bsteps.add_argument("--no-stop-on-error", action="store_true", help="Continue on error")
    bsteps.add_argument("--delay", type=float, default=0.3, help="Delay between steps in seconds")
    bsteps.add_argument("--verify", action="store_true", help="Dump UI after each step for verification")

    # ─── SLEEP ───
    sleep_p = sub.add_parser("sleep", help="Wait N seconds")
    sleep_p.add_argument("seconds", type=str)

    # ─── MACRO ───
    macro = sub.add_parser("macro", help="Macro recording/playback")
    m_sub = macro.add_subparsers(dest="macro_cmd")

    m_rec = m_sub.add_parser("record", help="Start recording")
    m_rec.add_argument("name", type=str)

    m_play = m_sub.add_parser("play", help="Play macro")
    m_play.add_argument("name", type=str)

    m_sub.add_parser("list", help="List macros")

    m_del = m_sub.add_parser("delete", help="Delete macro")
    m_del.add_argument("name", type=str)

    # ─── NOTIFICATION ───
    notif_p = sub.add_parser("notification", help="Notification interaction")
    n_sub = notif_p.add_subparsers(dest="notif_cmd")

    n_list = n_sub.add_parser("list", help="List notifications")
    n_list.add_argument("--count", type=int, default=10)

    n_tap = n_sub.add_parser("tap", help="Tap notification")
    n_tap.add_argument("index", type=str)

    n_reply = n_sub.add_parser("reply", help="Reply to notification")
    n_reply.add_argument("index", type=str)
    n_reply.add_argument("content", type=str)

    n_dismiss = n_sub.add_parser("dismiss", help="Dismiss notification")
    n_dismiss.add_argument("index", nargs="?", default=None)
    n_dismiss.add_argument("--all", action="store_true")

    n_sub.add_parser("expand", help="Expand notification shade")
    n_sub.add_parser("collapse", help="Collapse notification shade")

    # ─── HEALTH / STATUS ───
    status = sub.add_parser("status", help="Health check")
    status.add_argument("--force", action="store_true", help="Skip cache")

    sub.add_parser("health", help="Alias for status")

    # ─── SAFETY ───
    safety = sub.add_parser("safety", help="Safety check")
    safety_sub = safety.add_subparsers(dest="safety_cmd")
    safety_sub.add_parser("check", help="Run safety check")
    audit = safety_sub.add_parser("audit", help="View audit log")
    audit.add_argument("--lines", type=int, default=20)

    # ─── IME ───
    ime_p = sub.add_parser("ime", help="IME management")
    ime_sub = ime_p.add_subparsers(dest="ime_cmd")
    ime_sub.add_parser("detect", help="Detect current IME")
    ime_switch = ime_sub.add_parser("switch", help="Switch to FastInputIME")
    ime_switch.add_argument("--keep-ime", action="store_true")
    ime_rest = ime_sub.add_parser("restore", help="Restore original IME")
    ime_rest.add_argument("ime_id", nargs="?", default=None)
    ime_rest.add_argument("--keep-ime", action="store_true")

    return parser


def _ensure_screen_ready(args):
    """Auto wake + swipe unlock if screen is off or locked. Skips for non-interactive commands."""
    import time
    cmd = args.command
    # Commands that don't need the screen to be on/unlocked
    skip_commands = {"status"}
    if cmd in skip_commands:
        return
    # Device subcommands that manage screen state themselves
    if cmd == "device" and getattr(args, "device_cmd", None) in (
        "screen-on", "screen-off", "is-screen-on", "unlock", "lock",
        "reboot", "info", "battery",
    ):
        return
    try:
        from phone.connection import get_device, adb_shell
        import phone.config as cfg
        device = get_device(getattr(args, "device", None))
        # Wake screen if off
        if not device.info.get("screenOn"):
            device.press("power")
            time.sleep(0.5)
        # Check if keyguard (lock screen) is showing
        out, _ = adb_shell("dumpsys window | grep -i 'mDreamingLockscreen\\|isStatusBarKeyguard\\|showing=true\\|mShowingLockscreen'")
        is_locked = "mShowingLockscreen=true" in out or "isStatusBarKeyguard=true" in out or "mDreamingLockscreen=true" in out
        if not is_locked:
            # Fallback: also check via keyguard service
            out2, _ = adb_shell("dumpsys window policy | grep -i 'mShowingLockscreen\\|isKeyguardShowing'")
            is_locked = "mShowingLockscreen=true" in out2 or "isKeyguardShowing=true" in out2
        if is_locked:
            w, h = cfg.get_screen_size()
            device.swipe(w // 2, h * 3 // 4, w // 2, h // 4, duration=0.3)
            time.sleep(0.3)
    except Exception:
        pass  # Best effort; let the actual command handle errors


def dispatch(args):
    """Route parsed args to the correct handler."""
    cmd = args.command
    _ensure_screen_ready(args)

    if cmd == "ui":
        from phone.ui import cmd_dump, cmd_find, cmd_exists, cmd_current, cmd_watch, cmd_diff
        ui_cmd = args.ui_cmd
        if ui_cmd == "dump":
            cmd_dump(args)
        elif ui_cmd == "find":
            cmd_find(args)
        elif ui_cmd == "exists":
            cmd_exists(args)
        elif ui_cmd == "current":
            cmd_current(args)
        elif ui_cmd == "watch":
            cmd_watch(args)
        elif ui_cmd == "diff":
            cmd_diff(args)
        else:
            utils.error("Unknown ui subcommand. Use: dump, find, exists, current, watch, diff")

    elif cmd == "input":
        from phone.input_ctrl import (
            cmd_tap, cmd_tap_text, cmd_tap_id, cmd_tap_desc, cmd_tap_nth,
            cmd_long_tap, cmd_double_tap, cmd_swipe, cmd_swipe_dir, cmd_captcha_swipe,
            cmd_scroll_to, cmd_text, cmd_set_text, cmd_clear, cmd_key,
            cmd_pinch, cmd_drag, cmd_multi_tap, cmd_gesture
        )
        ic = args.input_cmd
        handlers = {
            "tap": cmd_tap, "tap-text": cmd_tap_text, "tap-id": cmd_tap_id,
            "tap-desc": cmd_tap_desc, "tap-nth": cmd_tap_nth, "long-tap": cmd_long_tap,
            "double-tap": cmd_double_tap, "swipe": cmd_swipe, "swipe-dir": cmd_swipe_dir,
            "scroll-to": cmd_scroll_to, "text": cmd_text, "set-text": cmd_set_text,
            "clear": cmd_clear, "key": cmd_key, "pinch": cmd_pinch, "drag": cmd_drag,
            "multi-tap": cmd_multi_tap, "gesture": cmd_gesture,
            "captcha-swipe": cmd_captcha_swipe,
        }
        if ic in handlers:
            handlers[ic](args)
        else:
            utils.error(f"Unknown input subcommand: {ic}")

    elif cmd == "device":
        from phone.device import (
            cmd_info, cmd_screen_on, cmd_screen_off, cmd_is_screen_on,
            cmd_unlock, cmd_lock, cmd_rotate, cmd_brightness, cmd_volume,
            cmd_wifi, cmd_bluetooth, cmd_airplane, cmd_mobile_data, cmd_hotspot,
            cmd_battery, cmd_reboot, cmd_dnd, cmd_nfc, cmd_gps, cmd_ime,
            cmd_stay_awake, cmd_check_a11y, cmd_restart_agent, cmd_ime_setup, cmd_ime_restore,
        )
        dc = args.device_cmd
        handlers = {
            "info": cmd_info, "screen-on": cmd_screen_on, "screen-off": cmd_screen_off,
            "is-screen-on": cmd_is_screen_on, "unlock": cmd_unlock, "lock": cmd_lock,
            "rotate": cmd_rotate, "brightness": cmd_brightness, "volume": cmd_volume,
            "wifi": cmd_wifi, "bluetooth": cmd_bluetooth, "airplane": cmd_airplane,
            "mobile-data": cmd_mobile_data, "hotspot": cmd_hotspot, "battery": cmd_battery,
            "reboot": cmd_reboot, "dnd": cmd_dnd, "nfc": cmd_nfc, "gps": cmd_gps,
            "ime": cmd_ime, "stay-awake": cmd_stay_awake, "check-a11y": cmd_check_a11y,
            "restart-agent": cmd_restart_agent, "ime-setup": cmd_ime_setup,
            "ime-restore": cmd_ime_restore,
        }
        if dc in handlers:
            handlers[dc](args)
        else:
            utils.error(f"Unknown device subcommand: {dc}")

    elif cmd == "app":
        from phone.app import (
            cmd_list, cmd_info, cmd_launch, cmd_stop, cmd_stop_all,
            cmd_install, cmd_uninstall, cmd_clear, cmd_current, cmd_recent,
            cmd_permissions, cmd_running, cmd_size, cmd_disable, cmd_enable,
        )
        ac = args.app_cmd
        handlers = {
            "list": cmd_list, "info": cmd_info, "launch": cmd_launch,
            "stop": cmd_stop, "stop-all": cmd_stop_all, "install": cmd_install,
            "uninstall": cmd_uninstall, "clear": cmd_clear, "current": cmd_current,
            "recent": cmd_recent, "permissions": cmd_permissions, "running": cmd_running,
            "size": cmd_size, "disable": cmd_disable, "enable": cmd_enable,
        }
        if ac in handlers:
            handlers[ac](args)
        else:
            utils.error(f"Unknown app subcommand: {ac}")

    elif cmd == "file":
        from phone.file_mgr import (
            cmd_push, cmd_pull, cmd_ls, cmd_rm, cmd_mkdir, cmd_cat, cmd_stat,
        )
        fc = args.file_cmd
        handlers = {
            "push": cmd_push, "pull": cmd_pull, "ls": cmd_ls,
            "rm": cmd_rm, "mkdir": cmd_mkdir, "cat": cmd_cat, "stat": cmd_stat,
        }
        if fc in handlers:
            handlers[fc](args)
        else:
            utils.error(f"Unknown file subcommand: {fc}")

    elif cmd == "screenshot":
        from phone.file_mgr import cmd_screenshot
        cmd_screenshot(args)

    elif cmd == "screenrecord":
        from phone.file_mgr import cmd_screenrecord_start, cmd_screenrecord_stop
        if args.sr_cmd == "start":
            cmd_screenrecord_start(args)
        elif args.sr_cmd == "stop":
            cmd_screenrecord_stop(args)
        else:
            utils.error("Use: screenrecord start | screenrecord stop")

    elif cmd == "sys":
        from phone.system import (
            cmd_processes, cmd_memory, cmd_storage, cmd_cpu, cmd_network,
            cmd_props, cmd_logcat, cmd_notifications, cmd_settings, cmd_date,
            cmd_uptime, cmd_thermal,
        )
        sc = args.sys_cmd
        handlers = {
            "processes": cmd_processes, "memory": cmd_memory, "storage": cmd_storage,
            "cpu": cmd_cpu, "network": cmd_network, "props": cmd_props,
            "logcat": cmd_logcat, "notifications": cmd_notifications, "settings": cmd_settings,
            "date": cmd_date, "uptime": cmd_uptime, "thermal": cmd_thermal,
        }
        if sc in handlers:
            handlers[sc](args)
        else:
            utils.error(f"Unknown sys subcommand: {sc}")

    elif cmd == "call":
        from phone.contacts import cmd_call, cmd_call_end, cmd_call_accept
        cc = args.call_cmd
        if cc == "dial":
            cmd_call(args)
        elif cc == "end":
            cmd_call_end(args)
        elif cc == "accept":
            cmd_call_accept(args)
        else:
            utils.error("Use: call dial <number> | call end | call accept")

    elif cmd == "sms":
        from phone.contacts import cmd_sms_send, cmd_sms_read
        if args.sms_cmd == "send":
            cmd_sms_send(args)
        elif args.sms_cmd == "read":
            cmd_sms_read(args)
        else:
            utils.error("Use: sms send | sms read")

    elif cmd == "contacts":
        from phone.contacts import cmd_contacts_list, cmd_contacts_add, cmd_contacts_delete
        cc = args.contacts_cmd
        if cc == "list":
            cmd_contacts_list(args)
        elif cc == "add":
            cmd_contacts_add(args)
        elif cc == "delete":
            cmd_contacts_delete(args)
        else:
            utils.error("Use: contacts list | contacts add | contacts delete")

    elif cmd == "media":
        from phone.media import (
            cmd_play_pause, cmd_next, cmd_prev, cmd_stop, cmd_camera,
            cmd_gallery, cmd_record_audio_start, cmd_record_audio_stop,
        )
        mc = args.media_cmd
        handlers = {
            "play-pause": cmd_play_pause, "next": cmd_next, "prev": cmd_prev,
            "stop": cmd_stop, "camera": cmd_camera, "gallery": cmd_gallery,
        }
        if mc in handlers:
            handlers[mc](args)
        elif mc == "record-audio":
            if getattr(args, "rec_cmd", None) == "start":
                cmd_record_audio_start(args)
            elif getattr(args, "rec_cmd", None) == "stop":
                cmd_record_audio_stop(args)
            else:
                utils.error("Use: media record-audio start | media record-audio stop")
        else:
            utils.error(f"Unknown media subcommand: {mc}")

    elif cmd == "wait":
        from phone.automation import cmd_wait_text, cmd_wait_gone, cmd_wait_activity
        wc = args.wait_cmd
        if wc == "text":
            cmd_wait_text(args)
        elif wc == "gone":
            cmd_wait_gone(args)
        elif wc == "activity":
            cmd_wait_activity(args)
        else:
            utils.error("Use: wait text | wait gone | wait activity")

    elif cmd == "assert":
        from phone.automation import cmd_assert_text, cmd_assert_not_text
        ac = args.assert_cmd
        if ac == "text":
            cmd_assert_text(args)
        elif ac == "not-text":
            cmd_assert_not_text(args)
        else:
            utils.error("Use: assert text | assert not-text")

    elif cmd == "shell":
        from phone.automation import cmd_shell
        cmd_shell(args)

    elif cmd == "intent":
        from phone.automation import cmd_intent
        cmd_intent(args)

    elif cmd == "clipboard":
        from phone.automation import cmd_clipboard_get, cmd_clipboard_set
        if args.clip_cmd == "get":
            cmd_clipboard_get(args)
        elif args.clip_cmd == "set":
            cmd_clipboard_set(args)
        else:
            utils.error("Use: clipboard get | clipboard set <content>")

    elif cmd == "open-url":
        from phone.automation import cmd_open_url
        cmd_open_url(args)

    elif cmd == "open-settings":
        from phone.automation import cmd_open_settings
        cmd_open_settings(args)

    elif cmd == "watcher":
        from phone.automation import cmd_watcher_add, cmd_watcher_remove, cmd_watcher_list
        wc = args.watcher_cmd
        if wc == "add":
            args.when_type = args.when_args[0] if args.when_args else "text"
            args.when_value = args.when_args[1] if args.when_args and len(args.when_args) > 1 else ""
            cmd_watcher_add(args)
        elif wc == "remove":
            cmd_watcher_remove(args)
        elif wc == "list":
            cmd_watcher_list(args)
        else:
            utils.error("Use: watcher add | watcher remove | watcher list")

    elif cmd == "toast":
        from phone.automation import cmd_toast
        cmd_toast(args)

    elif cmd == "location":
        from phone.automation import cmd_location_mock, cmd_location_mock_stop
        if args.loc_cmd == "mock":
            cmd_location_mock(args)
        elif args.loc_cmd == "mock-stop":
            cmd_location_mock_stop(args)
        else:
            utils.error("Use: location mock | location mock-stop")

    elif cmd == "batch":
        from phone.automation import cmd_batch
        cmd_batch(args)

    elif cmd == "batch-steps":
        from phone.automation import cmd_batch_steps
        cmd_batch_steps(args)

    elif cmd == "sleep":
        from phone.automation import cmd_sleep
        cmd_sleep(args)

    elif cmd == "macro":
        from phone.automation import cmd_macro_record, cmd_macro_play, cmd_macro_list, cmd_macro_delete
        mc = args.macro_cmd
        if mc == "record":
            cmd_macro_record(args)
        elif mc == "play":
            cmd_macro_play(args)
        elif mc == "list":
            cmd_macro_list(args)
        elif mc == "delete":
            cmd_macro_delete(args)
        else:
            utils.error("Use: macro record | macro play | macro list | macro delete")

    elif cmd == "notification":
        from phone.notification import (
            cmd_list, cmd_tap, cmd_reply, cmd_dismiss, cmd_expand, cmd_collapse,
        )
        nc = args.notif_cmd
        handlers = {
            "list": cmd_list, "tap": cmd_tap, "reply": cmd_reply,
            "dismiss": cmd_dismiss, "expand": cmd_expand, "collapse": cmd_collapse,
        }
        if nc in handlers:
            handlers[nc](args)
        else:
            utils.error(f"Unknown notification subcommand: {nc}")

    elif cmd in ("status", "health"):
        from phone.health import cmd_status
        cmd_status(args)

    elif cmd == "safety":
        from phone.safety import cmd_check, cmd_audit
        sc = args.safety_cmd
        if sc == "check":
            cmd_check(args)
        elif sc == "audit":
            cmd_audit(args)
        else:
            utils.error("Use: safety check | safety audit")

    elif cmd == "ime":
        from phone.ime import cmd_detect, cmd_switch_to_fast, cmd_restore
        ic = args.ime_cmd
        if ic == "detect":
            cmd_detect(args)
        elif ic == "switch":
            cmd_switch_to_fast(args)
        elif ic == "restore":
            cmd_restore(args)
        else:
            utils.error("Use: ime detect | ime switch | ime restore")

    else:
        utils.error(f"Unknown command: {cmd}. Run with -h for help.")


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # JSON output is default; --plain disables it
    if not getattr(args, "plain", False):
        utils.set_json_mode(True)

    # Build command name for timing
    cmd = args.command
    sub = ""
    for attr in ("ui_cmd", "input_cmd", "device_cmd", "app_cmd", "file_cmd",
                 "sys_cmd", "call_cmd", "sms_cmd", "contacts_cmd", "media_cmd",
                 "wait_cmd", "assert_cmd", "clip_cmd", "watcher_cmd", "loc_cmd",
                 "macro_cmd", "notif_cmd", "sr_cmd", "safety_cmd", "ime_cmd"):
        v = getattr(args, attr, None)
        if v:
            sub = v
            break
    cmd_name = f"{cmd} {sub}".strip() if sub else cmd
    utils.start_command_timer(cmd_name)

    # Capture stdout for verbose audit logging
    import io
    captured = io.StringIO()
    original_stdout = sys.stdout

    class TeeWriter:
        """Write to both original stdout and capture buffer."""
        def __init__(self, original, capture):
            self.original = original
            self.capture = capture
        def write(self, data):
            self.original.write(data)
            self.capture.write(data)
        def flush(self):
            self.original.flush()

    sys.stdout = TeeWriter(original_stdout, captured)
    cmd_args_str = " ".join(sys.argv[1:])

    try:
        dispatch(args)
        # Flush JSON result on success (skip if command handled its own output)
        if utils.is_json_mode() and not utils.is_output_handled():
            utils.flush_json_result(status="ok")
        # Verbose audit log
        sys.stdout = original_stdout
        output_text = captured.getvalue().strip()
        output_lines = output_text.split("\n") if output_text else []
        utils.audit_log_verbose(cmd_args_str, output_lines, result="OK")
    except SystemExit as e:
        sys.stdout = original_stdout
        output_text = captured.getvalue().strip()
        output_lines = output_text.split("\n") if output_text else []
        utils.audit_log_verbose(cmd_args_str, output_lines, result=f"EXIT:{e.code}")
        if e.code != 0 and utils.is_json_mode():
            pass  # error() already flushed JSON
        raise
    except KeyboardInterrupt:
        sys.stdout = original_stdout
        utils.audit_log_verbose(cmd_args_str, [], result="INTERRUPTED")
        if utils.is_json_mode():
            utils.flush_json_result(status="error", error_info={"message": "Interrupted"})
        else:
            print("\n[Interrupted]")
        sys.exit(130)
    except Exception as e:
        sys.stdout = original_stdout
        utils.audit_log_verbose(cmd_args_str, [], result=f"ERROR:{e}")
        utils.error(f"Unexpected error: {e}", cause=str(e))


if __name__ == "__main__":
    main()
