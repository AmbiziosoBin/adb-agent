# 验证码处理指南（AI 操作规范）

## 快速参考

```bash
# 截图 + 识别（最常用）
./captcha screenshot --x1 72 --y1 492 --x2 648 --y2 1106 --type 20226

# 滑动
./captcha swipe --x1 148 --y1 708 --x2 345 --y2 708 --duration 900

# 点击
./captcha tap --x 155 --y 745
```

**类型码**：缺口滑块 `20226` | 坐标点选 `88888` | 旋转图片 `900011` | 轨迹类型 `100016`

---

## 核心原则

**AI 负责判断，脚本负责执行。** 不要自己猜坐标，按以下流程操作：

## 操作流程

### 第一步：识别验证码类型 + 获取坐标信息

```bash
./phone ui dump --interactive --numbered
```
从输出中找：
- 有 `desc="actionImg"` 的元素 → **缺口滑块**，记录其 `center` 坐标（这是拖动把手位置）
- 有 `desc="basicImg"` 的元素 → 背景图，记录其 bounds 作为截图区域
- 有 WebView 且文字含"验证" → 记录 WebView 的 bounds 作为截图区域
- 多个需要按顺序点击的图片/文字 → **坐标点选**
- 可旋转的图片 → **旋转图片**
- 需要描绘轨迹 → **轨迹类型**

⚠️ **滑块把手识别**：不是所有页面都有 `desc="actionImg"`。如果 dump 中没有明确标识滑块把手的属性，你需要自行分析 UI 元素列表，找到最像滑块拖动把手的元素（通常是验证码区域底部的一个小的可拖动/可点击元素，宽度较窄、位于滑轨左侧起始位置）。以该元素的 `center` 坐标作为滑动起点。

### 第二步：截图并提交平台识别

用验证码容器的 bounds 截取区域，提交识别平台：

```bash
./captcha screenshot \
  --x1 <left> --y1 <top> --x2 <right> --y2 <bottom> \
  --type <类型码>
```

⚠️ **重要**：
- `recognition.screen_coords` 已经是**屏幕绝对坐标**，无论截全屏还是截区域，直接使用，不需要手动换算
- 截全屏时 offset 为 `[0, 0]`，截区域时 offset 为裁剪左上角，脚本自动处理
- `image_path` 是截图文件路径，可用于查看确认识别结果是否合理

### 第三步：根据识别结果执行操作

#### 缺口滑块

平台返回缺口的 X 轴偏移像素（如 `"197"`）。

从第一步找到的 `actionImg` center 出发，向右滑动偏移量：

```bash
# actionImg center = (148, 708)，偏移 = 197，目标 X = 148 + 197 = 345
python3 scripts/captcha_solver.py swipe \
  --x1 148 --y1 708 \
  --x2 345 --y2 708 \
  --duration 900
```

#### 坐标点选

平台返回格式：`"x1,y1|x2,y2|x3,y3"`，脚本已自动转换为屏幕坐标，直接从 `screen_coords` 取值按顺序点击：

```bash
./captcha tap --x <x1> --y <y1>
./captcha tap --x <x2> --y <y2>
./captcha tap --x <x3> --y <y3>
# ...依此类推
```

#### 旋转图片

平台返回旋转角度，从 `screen_coords.angle` 取值。找到旋转滑块条的位置，按比例滑动：

```bash
# 滑动距离 = angle / 360 * slider_width
./captcha swipe \
  --x1 <slider_left> --y1 <slider_y> \
  --x2 <slider_left + 滑动距离> --y2 <slider_y> \
  --duration 800
```

#### 轨迹类型

平台返回轨迹坐标序列，脚本已自动转换为屏幕坐标，从 `screen_coords` 取值，对相邻两点依次执行短距离 swipe：

```bash
./captcha swipe --x1 <p1.x> --y1 <p1.y> --x2 <p2.x> --y2 <p2.y> --duration 900
./captcha swipe --x1 <p2.x> --y1 <p2.y> --x2 <p3.x> --y2 <p3.y> --duration 100
# ...
```
