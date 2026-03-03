"""Utility functions: error handling, logging, retry, output formatting."""

import sys
import time
import functools
import datetime
import os
import json as _json
import traceback

from . import config as cfg

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ─── Global JSON output mode state ───
_json_mode = False
_cmd_start_time = None
_cmd_name = None
_output_lines = []      # collected output lines in JSON mode
_warnings = []          # collected warnings in JSON mode
_output_handled = False # set True when command handles its own JSON output


def set_json_mode(enabled):
    """Enable/disable JSON output mode."""
    global _json_mode
    _json_mode = enabled


def is_json_mode():
    return _json_mode


def mark_output_handled():
    """Mark that the command has handled its own output (skip flush_json_result)."""
    global _output_handled
    _output_handled = True


def is_output_handled():
    return _output_handled


def start_command_timer(command_name):
    """Start timing a command."""
    global _cmd_start_time, _cmd_name, _output_lines, _warnings, _output_handled
    _cmd_start_time = time.time()
    _cmd_name = command_name
    _output_lines = []
    _warnings = []
    _output_handled = False


def _ts():
    """Return current timestamp string."""
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _elapsed_ms():
    """Return elapsed ms since command start."""
    if _cmd_start_time:
        return int((time.time() - _cmd_start_time) * 1000)
    return 0


def flush_json_result(status="ok", error_info=None):
    """Flush collected output as a single JSON object. Called at end of command."""
    result = {
        "status": status,
        "command": _cmd_name or "",
        "timestamp": datetime.datetime.now().isoformat(),
        "duration_ms": _elapsed_ms(),
        "data": _output_lines,
    }
    if _warnings:
        result["warnings"] = _warnings
    if error_info:
        result["error"] = error_info
    print(_json.dumps(result, ensure_ascii=False))


def output(message):
    """Print a message to stdout (for AI to read)."""
    if _json_mode:
        _output_lines.append(str(message))
    else:
        print(message)


def error(message, hint=None, cause=None):
    """Print an error message and exit with code 1.
    
    Args:
        message: Error description
        hint: Suggested fix for the AI
        cause: Original exception or root cause detail
    """
    if _json_mode:
        error_info = {"message": str(message)}
        if hint:
            error_info["hint"] = hint
        if cause:
            error_info["cause"] = str(cause)
        flush_json_result(status="error", error_info=error_info)
        sys.exit(1)
    else:
        ts = _ts()
        elapsed = _elapsed_ms()
        parts = [f"[{ts}] [ERROR +{elapsed}ms] {message}"]
        if cause:
            parts.append(f"  原因: {cause}")
        if hint:
            parts.append(f"  建议: {hint}")
        print("\n".join(parts), file=sys.stderr)
        sys.exit(1)


def warn(message):
    """Print a warning message to stderr."""
    if _json_mode:
        _warnings.append(str(message))
    else:
        print(f"[{_ts()}] [WARN] {message}", file=sys.stderr)


def ok(message="OK"):
    """Print a success message."""
    if _json_mode:
        _output_lines.append(str(message))
    else:
        elapsed = _elapsed_ms()
        print(f"[{_ts()}] [OK +{elapsed}ms] {message}")


def retry(max_attempts=3, delay=1.0, exceptions=(Exception,)):
    """Decorator: retry a function on failure."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_err = e
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_err
        return wrapper
    return decorator


def audit_log(command, result="OK", detail=""):
    """Append an entry to the audit log file."""
    try:
        log_path = cfg.get_audit_log_path()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        elapsed = _elapsed_ms()
        line = f"[{ts}] [{elapsed}ms] CMD: {command} | RESULT: {result}"
        if detail:
            line += f" | {detail}"
        line += "\n"
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # Don't let logging errors break the tool


def audit_log_verbose(command_args, output_lines, result="OK"):
    """Append a detailed entry to the verbose audit log, including full output sent to AI."""
    try:
        log_path = cfg.get_audit_log_path().replace(".log", "_verbose.log")
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        elapsed = _elapsed_ms()
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{'='*80}\n")
            f.write(f"[{ts}] [{elapsed}ms] RESULT: {result}\n")
            f.write(f"CMD ARGS: {command_args}\n")
            if output_lines:
                f.write(f"OUTPUT ({len(output_lines)} lines):\n")
                for line in output_lines:
                    f.write(f"  {line}\n")
            f.write("\n")
    except Exception:
        pass


def truncate_text(text, max_len=None):
    """Truncate text to max length."""
    if text is None:
        return ""
    if max_len is None:
        max_len = cfg.load_config().get("output", {}).get("max_text_length", 50)
    text = str(text).strip()
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def format_size(size_bytes):
    """Format bytes to human readable string."""
    if size_bytes is None:
        return "N/A"
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def parse_bounds(bounds_str):
    """Parse '[x1,y1][x2,y2]' or '(x1,y1)(x2,y2)' to (x1, y1, x2, y2)."""
    import re
    m = re.findall(r'[\[\(](\d+),(\d+)[\]\)]', bounds_str)
    if len(m) == 2:
        return (int(m[0][0]), int(m[0][1]), int(m[1][0]), int(m[1][1]))
    return None


def center_of_bounds(bounds):
    """Get center point of bounds tuple (x1, y1, x2, y2)."""
    if bounds and len(bounds) == 4:
        return ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)
    return None
