"""Application management: list, info, launch, stop, install, uninstall, permissions."""

import re
import time

from .connection import get_device, adb_shell, adb_command
from .utils import output, error, ok, audit_log, format_size


def cmd_list(args):
    """List installed applications."""
    device = get_device(getattr(args, "device", None))
    flags = ""
    if getattr(args, "third_party", False):
        flags = "-3"
    elif getattr(args, "system", False):
        flags = "-s"

    out = device.shell(f"pm list packages {flags}").output
    packages = sorted([line.replace("package:", "").strip() for line in out.strip().split("\n") if line.strip()])

    search = getattr(args, "search", None)
    if search:
        search_lower = search.lower()
        packages = [p for p in packages if search_lower in p.lower()]

    for pkg in packages:
        output(pkg)
    output(f"\n[Total: {len(packages)}]")
    audit_log(f"app list {flags} {search or ''}")


def cmd_info(args):
    """Application detailed info."""
    device = get_device(getattr(args, "device", None))
    pkg = args.package

    out = device.shell(f"dumpsys package {pkg}").output
    if f"Unable to find package: {pkg}" in out:
        error(f"Package not found: {pkg}")

    # Extract key info
    version_match = re.search(r'versionName=(\S+)', out)
    version_code = re.search(r'versionCode=(\d+)', out)
    first_install = re.search(r'firstInstallTime=(.+)', out)
    last_update = re.search(r'lastUpdateTime=(.+)', out)

    output(f"package: {pkg}")
    output(f"version: {version_match.group(1) if version_match else 'N/A'}")
    output(f"versionCode: {version_code.group(1) if version_code else 'N/A'}")
    output(f"installed: {first_install.group(1).strip() if first_install else 'N/A'}")
    output(f"updated: {last_update.group(1).strip() if last_update else 'N/A'}")

    # Permissions
    perm_section = False
    perms = []
    for line in out.split("\n"):
        if "granted=true" in line:
            perm = re.search(r'android\.permission\.(\S+):', line)
            if perm:
                perms.append(perm.group(1))
    if perms:
        output(f"permissions: {', '.join(perms[:10])}")
        if len(perms) > 10:
            output(f"  ...and {len(perms) - 10} more")
    audit_log(f"app info {pkg}")


def cmd_launch(args):
    """Launch application."""
    device = get_device(getattr(args, "device", None))
    pkg = args.package
    activity = getattr(args, "activity", None)

    if activity:
        device.shell(f"am start -n {pkg}/{activity}")
    else:
        device.app_start(pkg)

    time.sleep(0.5)

    # Verify
    current = device.app_current()
    if current.get("package") == pkg:
        ok(f"Launched {pkg}")
    else:
        output(f"[WARN] Launched {pkg} but current foreground is {current.get('package')}")
    audit_log(f"app launch {pkg}")


def cmd_stop(args):
    """Force stop application."""
    device = get_device(getattr(args, "device", None))
    pkg = args.package
    device.app_stop(pkg)
    audit_log(f"app stop {pkg}")
    ok(f"Stopped {pkg}")


def cmd_stop_all(args):
    """Stop all third-party applications."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("pm list packages -3").output
    packages = [line.replace("package:", "").strip() for line in out.strip().split("\n") if line.strip()]

    count = 0
    for pkg in packages:
        try:
            device.app_stop(pkg)
            count += 1
        except Exception:
            pass

    audit_log(f"app stop-all ({count} apps)")
    ok(f"Stopped {count} third-party apps")


def cmd_install(args):
    """Install APK from local path or URL."""
    device = get_device(getattr(args, "device", None))
    source = args.source

    if source.startswith("http://") or source.startswith("https://"):
        output(f"Downloading from {source}...")
        device.app_install(source)
    else:
        # Local file - push and install via adb
        adb_command("install", "-r", source)

    audit_log(f"app install {source}")
    ok(f"Installed from {source}")


def cmd_uninstall(args):
    """Uninstall application."""
    if not getattr(args, "confirm", False):
        error("Uninstall requires --confirm flag for safety")

    device = get_device(getattr(args, "device", None))
    pkg = args.package
    keep_data = getattr(args, "keep_data", False)

    if keep_data:
        device.shell(f"pm uninstall -k {pkg}")
    else:
        device.app_uninstall(pkg)

    audit_log(f"app uninstall {pkg} keep_data={keep_data}")
    ok(f"Uninstalled {pkg}")


def cmd_clear(args):
    """Clear application data."""
    if not getattr(args, "confirm", False):
        error("Clear data requires --confirm flag for safety")

    device = get_device(getattr(args, "device", None))
    pkg = args.package
    device.app_clear(pkg)
    audit_log(f"app clear {pkg}")
    ok(f"Cleared data for {pkg}")


def cmd_current(args):
    """Current foreground application and activity."""
    device = get_device(getattr(args, "device", None))
    info = device.app_current()
    output(f'package: {info.get("package", "N/A")}')
    output(f'activity: {info.get("activity", "N/A")}')
    audit_log("app current")


def cmd_recent(args):
    """Recent applications (from recent tasks)."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("dumpsys activity recents | grep 'Recent #'").output
    lines = out.strip().split("\n")
    for line in lines[:10]:
        line = line.strip()
        if line:
            output(line)
    if not lines or not lines[0].strip():
        output("(no recent tasks found)")
    audit_log("app recent")


def cmd_permissions(args):
    """Manage application permissions."""
    device = get_device(getattr(args, "device", None))
    pkg = args.package

    grant_perm = getattr(args, "grant", None)
    revoke_perm = getattr(args, "revoke", None)

    if grant_perm:
        device.shell(f"pm grant {pkg} android.permission.{grant_perm}")
        ok(f"Granted {grant_perm} to {pkg}")
    elif revoke_perm:
        device.shell(f"pm revoke {pkg} android.permission.{revoke_perm}")
        ok(f"Revoked {revoke_perm} from {pkg}")
    else:
        # List permissions
        out = device.shell(f"dumpsys package {pkg} | grep 'android.permission'").output
        perms = []
        for line in out.strip().split("\n"):
            line = line.strip()
            if "granted=true" in line:
                perm = re.search(r'(android\.permission\.\S+):', line)
                if perm:
                    perms.append(f"  ✓ {perm.group(1)}")
            elif "granted=false" in line:
                perm = re.search(r'(android\.permission\.\S+):', line)
                if perm:
                    perms.append(f"  ✗ {perm.group(1)}")
        for p in perms[:20]:
            output(p)
        if len(perms) > 20:
            output(f"  ...and {len(perms) - 20} more")
    audit_log(f"app permissions {pkg}")


def cmd_running(args):
    """List running applications."""
    device = get_device(getattr(args, "device", None))
    out = device.shell("dumpsys activity activities | grep 'Run #'").output
    lines = out.strip().split("\n")
    seen = set()
    for line in lines:
        pkg_match = re.search(r'([a-zA-Z][a-zA-Z0-9_.]+)/\.', line)
        if pkg_match:
            pkg = pkg_match.group(1)
            if pkg not in seen:
                seen.add(pkg)
                output(pkg)
    output(f"\n[Running: {len(seen)}]")
    audit_log("app running")


def cmd_size(args):
    """Application storage usage."""
    device = get_device(getattr(args, "device", None))
    pkg = args.package
    out = device.shell(f"dumpsys package {pkg} | grep -E 'dataDir|codePath'").output
    output(f"package: {pkg}")
    for line in out.strip().split("\n"):
        if line.strip():
            output(line.strip())

    # Try to get size via pm
    size_out = device.shell(f"du -sh /data/data/{pkg} 2>/dev/null").output
    if size_out.strip():
        output(f"data size: {size_out.strip().split()[0]}")
    audit_log(f"app size {pkg}")


def cmd_disable(args):
    """Disable application."""
    device = get_device(getattr(args, "device", None))
    pkg = args.package
    device.shell(f"pm disable-user --user 0 {pkg}")
    audit_log(f"app disable {pkg}")
    ok(f"Disabled {pkg}")


def cmd_enable(args):
    """Enable application."""
    device = get_device(getattr(args, "device", None))
    pkg = args.package
    device.shell(f"pm enable {pkg}")
    audit_log(f"app enable {pkg}")
    ok(f"Enabled {pkg}")
