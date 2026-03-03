"""Safety mechanism: sensitive app/keyword detection, payment interception, audit log."""

import re

from .connection import get_device
from .utils import output, error, warn, audit_log
from .ui import _get_ui_xml, _parse_xml, _get_node_attrs
from . import config as cfg


def check_sensitive_app(device):
    """Check if current foreground app is in the sensitive list.
    Returns (is_sensitive, package_name).
    """
    try:
        current = device.app_current()
        pkg = current.get("package", "")
        sensitive = cfg.get_sensitive_packages()
        if pkg in sensitive:
            return True, pkg
        return False, pkg
    except Exception:
        return False, ""


def check_sensitive_keywords(xml_str):
    """Scan UI dump for sensitive keywords.
    Returns list of found keywords.
    """
    keywords = cfg.get_sensitive_keywords()
    found = []
    for kw in keywords:
        if kw in xml_str:
            found.append(kw)
    return found


def check_payment_screen(device):
    """Detect if current screen is a payment/transaction page.
    Returns (is_payment, details).
    """
    try:
        current = device.app_current()
        pkg = current.get("package", "")
        activity = current.get("activity", "")

        # Known payment activities
        payment_indicators = [
            ("com.eg.android.AlipayGphone", "pay"),
            ("com.tencent.mm", "pay"),
            ("com.tencent.mm", "WalletPayUI"),
        ]

        for p_pkg, p_kw in payment_indicators:
            if pkg == p_pkg and p_kw.lower() in activity.lower():
                return True, f"Payment activity detected: {pkg}/{activity}"

        # Check UI for payment keywords
        xml_str = _get_ui_xml(device, timeout=5)
        payment_keywords = ["确认付款", "立即支付", "输入支付密码", "验证指纹", "确认转账"]
        for kw in payment_keywords:
            if kw in xml_str:
                return True, f"Payment keyword found: {kw}"

        return False, ""
    except Exception:
        return False, ""


def pre_action_check(device, command=""):
    """Run safety checks before executing an action.
    Returns (safe_to_proceed, warning_message).

    Order matters:
    1. Payment screen detection first (catches payment pages in any app, including WeChat/Alipay)
    2. Sensitive package check second (blocks pure banking/finance apps entirely)
    """
    # 1. Check payment screen (activity + UI keywords) — works for WeChat Pay, Alipay pay pages, etc.
    is_payment, detail = check_payment_screen(device)
    if is_payment:
        return False, f"[SAFETY] Payment screen detected: {detail}. Click operations BLOCKED."

    # 2. Check sensitive app (pure banking/finance apps where ANY screen is sensitive)
    is_sensitive, pkg = check_sensitive_app(device)
    if is_sensitive:
        return False, f"[SAFETY] Sensitive app detected: {pkg}. Operation paused. Use --force to override."

    return True, ""


def require_confirm(command_name):
    """Check if a command requires --confirm flag."""
    dangerous_commands = [
        "uninstall", "clear", "reboot", "factory-reset",
        "rm", "delete", "wipe"
    ]
    return any(dc in command_name.lower() for dc in dangerous_commands)


def cmd_check(args):
    """Run safety check on current screen."""
    device = get_device(getattr(args, "device", None))

    output("[Safety Check]")

    # App check
    is_sensitive, pkg = check_sensitive_app(device)
    if is_sensitive:
        output(f"⚠ SENSITIVE APP: {pkg}")
    else:
        output(f"✓ App: {pkg} (safe)")

    # Payment check
    is_payment, detail = check_payment_screen(device)
    if is_payment:
        output(f"⚠ PAYMENT DETECTED: {detail}")
    else:
        output("✓ No payment screen detected")

    # Keyword check
    try:
        xml_str = _get_ui_xml(device, timeout=5)
        found_kw = check_sensitive_keywords(xml_str)
        if found_kw:
            output(f"⚠ SENSITIVE KEYWORDS: {', '.join(found_kw)}")
        else:
            output("✓ No sensitive keywords found")
    except Exception:
        output("○ Could not check keywords (UI dump failed)")

    audit_log("safety check")


def cmd_audit(args):
    """View recent audit log entries."""
    log_path = cfg.get_audit_log_path()
    lines_count = int(getattr(args, "lines", 20))

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[-lines_count:]:
            output(line.rstrip())
        output(f"\n[Showing last {min(lines_count, len(lines))} of {len(lines)} entries]")
    except FileNotFoundError:
        output("(no audit log yet)")
    except Exception as e:
        error(f"Failed to read audit log: {e}")
