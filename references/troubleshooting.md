# Troubleshooting Guide

## Connection Issues

### Device Not Found
**Symptom**: `No device found` or `adb devices` shows nothing

**Steps**:
1. Check USB cable is connected and phone shows USB debugging prompt
2. Run `adb devices` — if empty:
   - Reconnect USB cable
   - On phone: Settings → Developer Options → revoke USB debugging authorizations, then reconnect
   - Accept the "Allow USB debugging" prompt on phone
3. If WiFi ADB:
   ```bash
   adb connect <phone-ip>:5555
   ```
4. Check `config.yaml` has correct `wifi_ip` if using WiFi mode

### Device Offline
**Symptom**: `adb devices` shows `<serial> offline`

**Steps**:
1. Disconnect and reconnect USB
2. On phone: revoke USB debug authorizations, reconnect, accept prompt
3. `adb kill-server && adb start-server`
4. If persists, reboot phone

### WiFi ADB Disconnects
**Symptom**: WiFi connection drops after a while

**Steps**:
1. Ensure phone and Mac are on same WiFi network
2. Phone's IP may have changed — check in Settings → WiFi → current network
3. Re-establish: `adb tcpip 5555 && adb connect <new-ip>:5555`
4. Set static IP on phone to prevent IP changes
5. In `config.yaml`, set `wifi_ip` to the static IP

---

## u2 Agent Issues

### Agent Not Responding
**Symptom**: `u2 Agent: no response` in health check

**Steps**:
1. `python3 phone_control.py device restart-agent`
2. If that fails:
   ```bash
   python -m uiautomator2 init
   ```
3. On phone, check if "ATX" app is installed — if not, re-run init
4. Open ATX app on phone and tap "Start Service"

### Accessibility Service Disabled
**Symptom**: `Accessibility: (none)` in health check, UI dump returns empty/incomplete

**Steps**:
1. `python3 phone_control.py device check-a11y`
2. `python3 phone_control.py device restart-agent`
3. If ColorOS keeps disabling it:
   - Settings → Apps → ATX Agent → Battery → No restrictions
   - Settings → Apps → ATX Agent → Auto-launch → Allow
   - Settings → Accessibility → ATX Agent → Enable
4. ColorOS may show "accessibility service detected" warning — dismiss it

### Agent Killed by Battery Optimization
**Symptom**: Agent works then stops after a few minutes

**Steps**:
1. Phone Settings → Battery → App Battery Management → ATX Agent → "Don't optimize"
2. Lock ATX Agent in recent apps (swipe down to lock)
3. Disable ColorOS "Smart battery saver" temporarily during use

---

## Text Input Issues

### Chinese Text Input Fails
**Symptom**: `input text` shows garbled or no text appears

**Steps**:
1. Check current IME: `python3 phone_control.py ime detect`
2. Switch to FastInputIME: `python3 phone_control.py ime switch`
3. If popup appears about switching IME, it should auto-dismiss
4. If still fails:
   ```bash
   python3 phone_control.py device ime-setup
   ```
5. After operations, restore: `python3 phone_control.py ime restore`

### "USB Debugging (Security Settings)" Not Enabled
**Symptom**: Text input and taps don't work, even though device is connected

**Root cause**: ColorOS requires this special setting for u2 to simulate input

**Fix**:
1. Settings → Developer Options → "USB debugging (Security settings)" → Enable
2. This requires a reboot on some ColorOS versions
3. May require SIM card to be inserted

### FastInputIME Not Found
**Symptom**: `ime set` fails with "unknown IME"

**Steps**:
1. Re-initialize u2: `python -m uiautomator2 init`
2. This pushes the FastInputIME APK to the phone
3. Enable it: `adb shell ime enable com.github.uiautomator/.FastInputIME`

---

## UI Dump Issues

### UI Dump Timeout
**Symptom**: `Failed to dump UI hierarchy: timeout`

**Steps**:
1. Increase timeout: `ui dump --timeout 30`
2. The screen may be too complex (many elements). Try:
   - `ui dump --interactive` (fewer elements)
   - `ui dump --search "keyword"` (filtered)
   - `ui current` (no UI tree, just package/activity)
3. If consistent, restart agent: `python3 phone_control.py device restart-agent`

### Empty UI Dump
**Symptom**: Dump returns no elements

**Steps**:
1. Check accessibility service: `python3 phone_control.py device check-a11y`
2. The screen might be a system screen (lock screen, boot screen) with no accessibility
3. Try `python3 phone_control.py device screen-on` first
4. Some screens (video players, games) may not expose UI tree

### UI Dump Shows Wrong Screen
**Symptom**: Dump shows elements from a different app

**Steps**:
1. Check current app: `python3 phone_control.py ui current`
2. There might be an overlay/popup. Try `input key BACK` to dismiss
3. Split screen / PIP mode can mix UI trees — close split screen first

---

## Click/Tap Issues

### Tap Not Working
**Symptom**: `input tap` says OK but nothing happens on screen

**Steps**:
1. Verify coordinates with `ui dump --numbered` — coordinates may have changed
2. Check "USB debugging (Security settings)" is enabled
3. The element might not be truly clickable — try `input tap-text` instead
4. Element might be behind an overlay — check for popups

### Wrong Element Clicked
**Symptom**: Clicked something unexpected

**Steps**:
1. Always `ui dump --interactive --numbered` before clicking
2. Use `input tap-text "exact text"` for precision
3. If multiple elements have same text, use `input tap-id` with resource-id
4. Use `ui dump --search "text" --numbered` to narrow results

---

## ColorOS Specific Issues

### "Permission Monitor" Kills Agent
**Fix**: Developer Options → disable "Permission Monitor"

### Battery Saver Kills Background Services
**Fix**: 
- Settings → Battery → disable "Smart Power Saver"
- Settings → Apps → ATX Agent → Battery → No restrictions
- Lock ATX in recent apps

### Popup: "New Input Method Detected"
**Symptom**: ColorOS shows notification about FastInputIME

**Fix**: The tool auto-handles this. If it persists:
1. Manually dismiss the notification
2. Settings → System → Keyboard → manage keyboards → allow FastInputIME

### Auto-close of Accessibility Services
**Symptom**: ColorOS disables ATX accessibility service periodically

**Fix**:
1. This is a ColorOS "feature" — it disables third-party accessibility services
2. Workaround: `python3 phone_control.py device restart-agent` when needed
3. Some ColorOS versions have a setting to whitelist accessibility services

---

## Safety / Payment Issues

### Operation Blocked by Safety Check
**Symptom**: `[SAFETY] Sensitive app detected` or `Payment screen detected`

**This is intentional.** The tool blocks operations on payment screens.

**If you need to operate**: 
- Navigate away from the payment screen first
- Complete the payment manually
- Then resume AI control

### Audit Log
Check what operations were performed:
```bash
python3 phone_control.py safety audit --lines 50
```

---

## Performance Tips

1. **Use `ui current` instead of `ui dump`** when you just need to know which app/activity is showing
2. **Use `--interactive --numbered`** to get only actionable elements
3. **Use `--search`** to filter elements when looking for something specific
4. **Use `ui diff`** after operations instead of full re-dump
5. **Set up watchers** for common popups to reduce back-and-forth
6. **Cache device info** in config.yaml so you don't query it every time
