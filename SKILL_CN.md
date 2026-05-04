---
name: adb-agent
description: 通过 ADB 和 uiautomator2 控制 Android 手机。当用户要求操作手机、打开应用、点击按钮、输入文字、滚动、截图、安装/卸载应用、调整设置、锁屏/解锁、发消息、打电话或任何其他手机交互时使用。也适用于用户说"帮我用手机..."/"在手机上..."/"打开手机..."/"手机帮我..."时。
metadata:
  {
    "openclaw": {
      "emoji": "📱",
      "os": ["darwin", "linux", "win32"],
      "requires": { "bins": ["adb", "python3"] }
    }
  }
---

# Android 手机控制

通过 ADB + uiautomator2 使用 `phone_control.py` 控制 Android 手机。

## 何时使用

**使用场景**：用户要求操作手机、打开应用、点击/输入/滚动、安装应用、调整设置、锁屏/解锁、截图、发消息、打电话、检查状态，或说"帮我.../在手机上.../用手机.../打开..."

## 设置

所有命令使用技能目录中的 `phone` 包装脚本，会自动激活 Python 虚拟环境。

所有命令的工作目录：`~/.openclaw/workspace/skills/adb-agent`

## 快速开始

```bash
./phone status                              # 检查连接
./phone ui dump --interactive --numbered    # 查看屏幕（始终第一步）
./phone input tap-nth 3                     # 按 dump 中的索引点击
./phone input tap-text "搜索"                # 按文本点击
./phone input tap-text "搜索" --index 2     # 点击第 2 个匹配项
./phone input text "你好世界"               # 输入文字（支持中文）
./phone app launch com.tencent.mm           # 启动应用
./phone input key BACK                      # 返回/主页
./phone ui current                          # 快速检查（节省 token）
./phone screenshot                          # 截图（通过 MEDIA: 发送给用户）
./phone --plain input tap-text "确定"       # --plain 输出文本格式（默认 JSON）
```

## 操作原则

**🔴 关键：在关键步骤截图** — 在以下三种场景调用 `./phone screenshot`：
1. **启动应用后** — 验证应用正确打开
2. **任务完成后** — 向用户展示最终结果
3. **需要用户确认时** — 弹窗、验证码、意外屏幕

命令输出 `MEDIA:<path>` 会自动触发 OpenClaw 将图片发送给用户。只需调用命令，让 OpenClaw 处理显示。

1. **先看后动**：操作前先 `ui dump --interactive --numbered`
2. **操作后验证**：重新 dump 确认生效，关键操作检查 UI 元素变化
3. **用 app launch 打开应用**：不要回桌面点图标，用 `./phone app launch <package>`
4. **等待加载**：启动应用后用 `wait text`
5. **batch-steps 避免弹窗操作**：不要把"获取验证码"等放进 batch（详见 [batch-steps 详解](references/batch-steps.md)）
6. **验证码处理**：遇到滑块/点击验证码，查阅 [验证码处理手册](references/captcha.md)
7. **dump 是快照**：操作后索引会变，tap-nth 前必须重新 dump
8. **截图自动发送**：`./phone screenshot` 自动通过 MEDIA: 发送，不要 read 文件
9. **UI dump 详解**：不清楚输出格式时查阅 [UI dump 解读](references/ui-dump.md)
10. **遇到问题先查文档**：[故障排除](references/troubleshooting.md) 或 [命令参考](references/commands.md)

## 批量步骤（多步操作）

当你已经知道要执行的 UI 操作序列时，使用 `batch-steps` 在**一条命令**中执行它们。这避免了多次 AI↔工具往返，节省时间和 token。

```bash
# 一次调用执行多步登录流程：
./phone batch-steps '[{"action":"input","command":"tap-text","args":{"text":"手机号"}},{"action":"input","command":"text","args":{"content":"13800138000"}},{"action":"input","command":"tap-text","args":{"text":"同意"}},{"action":"input","command":"tap-text","args":{"text":"获取验证码"}}]'
```

**UI 变化自动检测**：batch-steps 会自动检测非预期的 UI 变化（弹窗、对话框、activity 跳转）并中断执行。中断时会在 JSON 前输出警告，并在 JSON 的 `current_ui` 字段附带当前 UI 快照供分析。

**关键点**：
- 每步格式：`{"action": "input/wait/app/ui/device/shell/sleep", "command": "tap-text/text/key/...", "args": {...}}`
- 选项：`--delay 0.3`、`--stop-on-error`、`--verify`、`--no-ui-check`
- ⚠️ 避免在 batch-steps 中包含可能触发弹窗的操作（"获取验证码"、"提交"、"支付"）

完整 JSON 格式、支持的操作和示例见 [batch-steps 详解](references/batch-steps.md)。

## UI Dump 输出格式

`ui dump --interactive --numbered` 先输出滚动提示（文本），然后是 JSON：
- **滚动提示**（`[重要提示]`）：先读这个！它告诉你页面是否可滚动，并提供可直接使用的滑动命令
- **元素字段**：`index`（用于 tap-nth）、`text`、`desc`、`center` [x,y]、`clickable`（布尔值）、`scrollable`/`selected`/`checked`（为 true 时）
- **根字段**：`package`、`activity`、`screen` {width,height}

详细字段说明和示例见 [UI dump 解读](references/ui-dump.md)。

## 验证码处理

⚠️ **遇到验证码时，必须先用 read 工具阅读 `references/captcha.md` 获取完整处理流程，不要自行猜测坐标或乱试。**

验证码处理依赖 `scripts/captcha_solver.py` 调用第三方识别平台，AI 只需要：
1. 从 UI dump 分析验证码类型和元素位置
2. 调用 `captcha_solver.py screenshot` 截图并提交识别
3. 根据识别结果执行滑动/点击

详细流程见 [验证码处理手册](references/captcha.md)，**必须先 read 该文件再操作**。

---

## 详细文档索引

遇到以下场景时，查阅对应文档：

- 📋 [所有命令参考](references/commands.md) — 完整命令列表和参数说明
- 🎯 [常见场景示例](references/scenarios.md) — 发消息、搜索、登录等实战案例
- 🔧 [故障排除](references/troubleshooting.md) — 常见错误和解决方案
- 🤖 [验证码处理](references/captcha.md) — 滑块/点击验证码完整流程
- 📦 [batch-steps 详解](references/batch-steps.md) — 批量操作、UI 变化检测
- 🎨 [UI dump 解读](references/ui-dump.md) — dump 输出格式、元素字段说明
