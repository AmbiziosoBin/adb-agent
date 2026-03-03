# Common Scenario Operation Guide

## Basic Operations

### 1. Check Phone Status
```bash
python3 phone_control.py status
```
One command shows: ADB connection, u2 Agent, accessibility, screen, IME, latency, battery.

### 2. Wake Up and Unlock Phone
```bash
python3 phone_control.py device screen-on
python3 phone_control.py device unlock --swipe
# With PIN:
python3 phone_control.py device unlock --pin 1234
# Verify:
python3 phone_control.py ui current
```

### 3. View Current Screen
```bash
# Quick check (saves tokens)
python3 phone_control.py ui current
# Full interactive view
python3 phone_control.py ui dump --interactive --numbered
# Search for specific text
python3 phone_control.py ui dump --search "下载" --numbered
```

---

## App Operations

### 4. Open App and Navigate
```bash
# Launch WeChat
python3 phone_control.py app launch com.tencent.mm
python3 phone_control.py wait text "微信" --timeout 10
python3 phone_control.py ui dump --interactive --numbered
# Tap based on what you see
python3 phone_control.py input tap-nth 5
```

### 5. Search and Install App from App Store
```bash
# Open device App Store (example: OPPO market, adjust for your device)
python3 phone_control.py app launch com.oppo.market
python3 phone_control.py wait text "搜索" --timeout 10
python3 phone_control.py ui dump --interactive --numbered

# Find and tap search
python3 phone_control.py input tap-text "搜索"
python3 phone_control.py input text "抖音"
python3 phone_control.py input key ENTER

# Wait for results
python3 phone_control.py wait text "安装" --timeout 15
python3 phone_control.py ui dump --search "安装" --numbered

# Tap install button
python3 phone_control.py input tap-nth 1
# Wait for installation
python3 phone_control.py wait text "打开" --timeout 120
```

### 6. Uninstall App
```bash
python3 phone_control.py app uninstall com.example.app --confirm
```

### 7. Force Stop Misbehaving App
```bash
python3 phone_control.py app stop com.example.app
# Or stop all third-party apps
python3 phone_control.py app stop-all
```

---

## Messaging

### 8. Send WeChat Message
```bash
python3 phone_control.py app launch com.tencent.mm
python3 phone_control.py wait text "微信" --timeout 10
python3 phone_control.py ui dump --interactive --numbered

# Search for contact
python3 phone_control.py input tap-text "搜索"
python3 phone_control.py input text "张三"
python3 phone_control.py wait text "张三" --timeout 5
python3 phone_control.py input tap-text "张三"

# Wait for chat to open
python3 phone_control.py wait text "发送" --timeout 5

# Find input field and type
python3 phone_control.py ui dump --interactive --numbered
# Tap the message input field (usually the last EditText)
python3 phone_control.py input tap-nth <N>
python3 phone_control.py input text "我晚点到"
python3 phone_control.py input tap-text "发送"

# Verify
python3 phone_control.py ui dump --search "我晚点到"
```

### 9. Send SMS
```bash
python3 phone_control.py sms send 13800138000 "明天见"
# This opens SMS compose, may need to tap Send button
python3 phone_control.py ui dump --interactive --numbered
python3 phone_control.py input tap-text "发送"
```

### 10. Make a Phone Call
```bash
python3 phone_control.py call dial 13800138000
# To hang up:
python3 phone_control.py call end
```

---

## Settings Adjustments

### 11. Connect to WiFi
```bash
python3 phone_control.py device wifi status
python3 phone_control.py device wifi on
python3 phone_control.py device wifi connect "MyWiFi" --wifi-password "password123"
```

### 12. Adjust Volume and Brightness
```bash
# Volume
python3 phone_control.py device volume media set 8
python3 phone_control.py device volume ring mute

# Brightness
python3 phone_control.py device brightness 150
python3 phone_control.py device brightness auto
```

### 13. Toggle Airplane Mode
```bash
python3 phone_control.py device airplane on
python3 phone_control.py device airplane off
```

### 14. Open Specific Settings Page
```bash
python3 phone_control.py open-settings wifi
python3 phone_control.py open-settings bluetooth
python3 phone_control.py open-settings display
python3 phone_control.py open-settings developer
```

---

## Screenshot and Recording

### 15. Take Screenshot
```bash
python3 phone_control.py screenshot
python3 phone_control.py screenshot --filename "my_screenshot.png"
python3 phone_control.py screenshot --element "搜索框"
```

### 16. Record Screen
```bash
python3 phone_control.py screenrecord start --duration 30
# ... do things ...
python3 phone_control.py screenrecord stop
```

---

## Notification Handling

### 17. Check and Handle Notifications
```bash
python3 phone_control.py notification expand
python3 phone_control.py notification list --count 5
# Tap to open a notification
python3 phone_control.py notification tap 0
# Reply inline
python3 phone_control.py notification reply 0 "收到"
# Dismiss all
python3 phone_control.py notification dismiss --all
```

---

## Auto Popup Handling

### 18. Setup Auto-Dismiss for Common Popups
```bash
# Auto-click "允许" for permission dialogs
python3 phone_control.py watcher add allow --when text "允许" --do click
# Auto-click "同意" for terms
python3 phone_control.py watcher add agree --when text "同意" --do click
# Auto-skip ads
python3 phone_control.py watcher add skip_ad --when text "跳过" --do click
# Auto-dismiss update prompts
python3 phone_control.py watcher add dismiss_update --when text "以后再说" --do click

# Check active watchers
python3 phone_control.py watcher list

# Remove when done
python3 phone_control.py watcher remove --all
```

---

## Scrolling and Navigation

### 19. Scroll Through a List
```bash
# Scroll down
python3 phone_control.py input swipe-dir up
# Scroll until target appears
python3 phone_control.py input scroll-to "关于手机"
# Check what's on screen now
python3 phone_control.py ui dump --interactive --numbered
```

### 20. Navigate Back and Home
```bash
python3 phone_control.py input key BACK
python3 phone_control.py input key HOME
python3 phone_control.py input key RECENT_APPS
```

---

## Advanced: Batch and Macro

### 21. Create and Run a Macro
```bash
# Create macro template
python3 phone_control.py macro record morning_routine
# Edit the macro file to add commands, then play:
python3 phone_control.py macro play morning_routine
```

### 22. Open URL
```bash
python3 phone_control.py open-url "https://www.baidu.com"
```

### 23. Clipboard Operations
```bash
python3 phone_control.py clipboard set "要粘贴的内容"
python3 phone_control.py clipboard get
```

---

## Troubleshooting Flows

### 24. Fix Text Input Not Working
```bash
python3 phone_control.py device ime-setup
# After done:
python3 phone_control.py device ime-restore
```

### 25. Fix Agent Crash
```bash
python3 phone_control.py device check-a11y
python3 phone_control.py device restart-agent
python3 phone_control.py status
```

### 26. Check Safety Before Operating
```bash
python3 phone_control.py safety check
python3 phone_control.py safety audit --lines 10
```

---

## Tips for AI

1. **Always `ui dump --interactive --numbered` before clicking** — don't guess coordinates
2. **Use `ui current` for quick checks** — much cheaper than full dump
3. **Use `wait text` after launching apps** — don't click blindly
4. **Set up watchers early** — saves many rounds handling popups
5. **Use `--search` to find specific elements** — much smaller output
6. **After failed operations, dump again** — the UI may have changed
7. **For text input, check IME first** — `ime detect`, then `ime switch` if needed
8. **Use `ui diff` after operations** — see what changed without full re-dump
