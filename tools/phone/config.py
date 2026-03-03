"""Configuration management for phone control tool."""

import os
import yaml

# Default config file path (relative to the skill root)
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_CONFIG_PATH = os.path.join(_SKILL_ROOT, "config.yaml")

_cached_config = None


def _deep_merge(base, override):
    """Merge override dict into base dict recursively."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# Default configuration
DEFAULTS = {
    "device": "",
    "mode": "usb",
    "wifi_ip": "",
    "wifi_port": 5555,
    "timeouts": {
        "ui_dump": 15,
        "input_action": 10,
        "app_launch": 15,
        "install": 120,
        "screenshot": 10,
        "connect": 10,
        "reconnect_interval": 5,
        "reconnect_retries": 3,
    },
    "output": {
        "max_ui_depth": 20,
        "max_text_length": 50,
        "compact_separator": " | ",
    },
    "sensitive_packages": [
        "com.eg.android.AlipayGphone",
        "com.android.bankabc",
        "com.icbc",
        "com.chinamworld.bocmbci",
        "com.CCB",
        "com.cmb.pb",
    ],
    "sensitive_keywords": [
        "支付", "付款", "转账", "密码", "银行卡", "余额", "确认付款", "输入密码",
    ],
    "audit_log": "phone_control_audit.log",
    "screen": {
        "width": 1080,
        "height": 2400,
    },
}


def load_config(config_path=None):
    """Load config from YAML file, merged with defaults."""
    global _cached_config
    if _cached_config is not None and config_path is None:
        return _cached_config

    cfg = DEFAULTS.copy()
    path = config_path or _DEFAULT_CONFIG_PATH

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
            cfg = _deep_merge(cfg, user_cfg)
        except Exception:
            pass  # Use defaults on parse error

    if config_path is None:
        _cached_config = cfg
    return cfg


def get_timeout(key):
    """Get a specific timeout value."""
    cfg = load_config()
    return cfg.get("timeouts", {}).get(key, 10)


def get_sensitive_packages():
    """Get list of sensitive package names."""
    cfg = load_config()
    return cfg.get("sensitive_packages", [])


def get_sensitive_keywords():
    """Get list of sensitive keywords."""
    cfg = load_config()
    return cfg.get("sensitive_keywords", [])


def get_screen_size():
    """Get configured screen size as (width, height)."""
    cfg = load_config()
    s = cfg.get("screen", {})
    return s.get("width", 1080), s.get("height", 2400)


def get_audit_log_path():
    """Get audit log file path."""
    cfg = load_config()
    log_path = cfg.get("audit_log", "phone_control_audit.log")
    if not os.path.isabs(log_path):
        log_path = os.path.join(_SKILL_ROOT, log_path)
    return log_path
