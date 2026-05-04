#!/usr/bin/env python3
"""
captcha_solver.py — 验证码辅助脚本（AI 主导版）

AI 负责所有判断，脚本只负责执行 ADB 操作和调用识别平台。

子命令:
  screenshot  截取指定区域，提交平台识别，返回识别结果给 AI
  swipe       ADB 原生滑动
  tap         ADB 原生点击

用法示例:
  # AI 发现滑块验证码，截取验证码区域并识别（坐标从 UI dump 获取）
  python3 captcha_solver.py screenshot --x1 72 --y1 492 --x2 648 --y2 1106 --type 20226

  # AI 分析识别结果后，告诉脚本滑动
  python3 captcha_solver.py swipe --x1 148 --y1 732 --x2 439 --y2 732

  # AI 告诉脚本点击
  python3 captcha_solver.py tap --x 155 --y 745

类型码:
  20226  / 20225 / 22222 — 缺口滑块
  88888              — 坐标点选
  900011             — 旋转图片
  100016             — 轨迹类型
"""

import sys
import os
import argparse
import base64
import json
import subprocess
import datetime
import requests

MEDIA_DIR = os.path.expanduser("~/.openclaw/media/phone")
API_URL   = "http://api.jfbym.com/api/YmServer/customApi"
API_TOKEN = "dSpZAGt8MnwLTPMNqKRDD6qUvPriEE0KKXpd-Iy2w6U"

TYPE_NAMES = {
    "20226": "缺口滑块", "20225": "缺口滑块(备用1)", "22222": "缺口滑块(备用2)",
    "88888": "坐标点选", "900011": "旋转图片", "100016": "轨迹类型",
}
# 识别失败时自动降级尝试
FALLBACK = {"20226": ["20225", "22222"]}


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", file=sys.stderr)


def adb(*args, timeout=10):
    """执行 adb 命令，返回 (stdout, returncode)。"""
    result = subprocess.run(["adb"] + list(args),
                            capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.returncode


# ─── screenshot 子命令 ───────────────────────────────────────────────────────

def cmd_screenshot(args):
    """
    用 adb screencap 截图，可选裁剪区域。
    提交平台识别（如果指定了 --type）。
    输出 JSON: { status, image_base64, image_path, recognition }
    """
    os.makedirs(MEDIA_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    remote = "/sdcard/captcha_tmp.png"
    local  = os.path.join(MEDIA_DIR, f"captcha_{ts}.png")

    # adb screencap 原始截图
    log("📸 adb screencap...")
    adb("shell", "screencap", "-p", remote)
    adb("pull", remote, local)
    adb("shell", "rm", remote)

    # 裁剪（如果指定了区域）
    x1, y1, x2, y2 = args.x1, args.y1, args.x2, args.y2
    if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
        from PIL import Image
        img = Image.open(local)
        img = img.crop((x1, y1, x2, y2))
        local = os.path.join(MEDIA_DIR, f"captcha_crop_{ts}.png")
        img.save(local)
        log(f"  ✂️ 裁剪: ({x1},{y1})-({x2},{y2}) → {img.size[0]}x{img.size[1]}")
    else:
        from PIL import Image
        img = Image.open(local)
        log(f"  全屏: {img.size[0]}x{img.size[1]}")

    # base64 编码
    with open(local, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    output = {
        "status": "ok",
        "image_path": local,
        "crop": {"x1": x1, "y1": y1, "x2": x2, "y2": y2} if x1 is not None else None,
        "recognition": None,
    }

    # 调用识别平台（如果指定了类型码）
    if args.type:
        type_codes = [args.type] + FALLBACK.get(args.type, [])
        for tc in type_codes:
            log(f"🔄 提交识别 type={tc} ({TYPE_NAMES.get(tc, tc)})...")
            try:
                resp = requests.post(API_URL, json={
                    "image": b64, "token": API_TOKEN, "type": tc
                }, timeout=30)
                result = resp.json()
            except Exception as e:
                log(f"  ❌ 请求失败: {e}")
                continue

            log(f"  📨 返回: {json.dumps(result, ensure_ascii=False)}")
            if result.get("code") == 10000:
                data = result["data"].get("data", "")
                log(f"  ✅ 识别成功: {data}")

                # 将平台返回的坐标转换为屏幕绝对坐标
                offset_x = x1 if x1 is not None else 0
                offset_y = y1 if y1 is not None else 0
                screen_coords = _to_screen_coords(data, tc, offset_x, offset_y)

                output["recognition"] = {
                    "type_code": tc,
                    "type_name": TYPE_NAMES.get(tc, tc),
                    "data": data,           # 平台原始数据
                    "screen_coords": screen_coords,  # 已转换为屏幕绝对坐标，直接使用
                    "offset": [offset_x, offset_y],
                }
                break
            else:
                log(f"  ⚠️ 识别失败 code={result.get('code')}, 尝试下一个...")

    print(json.dumps(output, ensure_ascii=False))


# ─── swipe 子命令 ────────────────────────────────────────────────────────────

def cmd_swipe(args):
    """adb 原生滑动。"""
    x1, y1, x2, y2 = args.x1, args.y1, args.x2, args.y2
    duration = args.duration
    log(f"🖱️ adb swipe ({x1},{y1})->({x2},{y2}) {duration}ms")
    _, rc = adb("shell", "input", "swipe",
                str(x1), str(y1), str(x2), str(y2), str(duration))
    if rc == 0:
        print(json.dumps({"status": "ok", "action": "swipe",
                          "from": [x1, y1], "to": [x2, y2], "duration_ms": duration},
                         ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "message": "adb swipe 失败"}, ensure_ascii=False))
        sys.exit(1)


# ─── 坐标转换 ────────────────────────────────────────────────────────────────

def _to_screen_coords(data, type_code, offset_x, offset_y):
    """
    将平台返回的原始数据转换为屏幕绝对坐标。
    无论截全屏（offset=0,0）还是截区域（offset=裁剪左上角），结果都是屏幕坐标。

    返回格式因类型而异：
      缺口滑块: {"offset_px": 197}  — X 轴偏移量，不需要坐标转换
      坐标点选: [{"x": 155, "y": 745}, ...]  — 屏幕绝对坐标列表
      旋转图片: {"angle": 87}  — 角度，不需要坐标转换
      轨迹类型: [{"x": 100, "y": 200}, ...]  — 屏幕绝对坐标列表
    """
    try:
        # 缺口滑块：返回单个数字（X 偏移像素），无需坐标转换
        if type_code in ("20226", "20225", "22222"):
            return {"offset_px": int(float(data.strip()))}

        # 旋转图片：返回角度，无需坐标转换
        if type_code == "900011":
            return {"angle": float(data.strip())}

        # 坐标点选 / 轨迹类型：返回 "x1,y1|x2,y2|..." 格式
        if type_code in ("88888", "100016"):
            points = []
            for pair in data.strip().split("|"):
                parts = pair.strip().split(",")
                if len(parts) >= 2:
                    px = int(float(parts[0])) + offset_x
                    py = int(float(parts[1])) + offset_y
                    points.append({"x": px, "y": py})
            return points

    except Exception as e:
        log(f"  ⚠️ 坐标转换失败: {e}")

    return {"raw": data}


# ─── tap 子命令 ──────────────────────────────────────────────────────────────

def cmd_tap(args):
    """adb 原生点击。"""
    x, y = args.x, args.y
    log(f"👆 adb tap ({x},{y})")
    _, rc = adb("shell", "input", "tap", str(x), str(y))
    if rc == 0:
        print(json.dumps({"status": "ok", "action": "tap", "point": [x, y]},
                         ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "message": "adb tap 失败"}, ensure_ascii=False))
        sys.exit(1)


# ─── 入口 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="验证码辅助脚本（AI 主导）")
    sub = parser.add_subparsers(dest="cmd")

    # screenshot
    ss = sub.add_parser("screenshot", help="截图 + 可选平台识别")
    ss.add_argument("--x1", type=int, default=None, help="裁剪左上 X")
    ss.add_argument("--y1", type=int, default=None, help="裁剪左上 Y")
    ss.add_argument("--x2", type=int, default=None, help="裁剪右下 X")
    ss.add_argument("--y2", type=int, default=None, help="裁剪右下 Y")
    ss.add_argument("--type", type=str, default=None,
                    help="验证码类型码: 20226/88888/900011/100016")

    # swipe
    sw = sub.add_parser("swipe", help="ADB 滑动")
    sw.add_argument("--x1", type=int, required=True)
    sw.add_argument("--y1", type=int, required=True)
    sw.add_argument("--x2", type=int, required=True)
    sw.add_argument("--y2", type=int, required=True)
    sw.add_argument("--duration", type=int, default=900, help="滑动时长 ms（默认 900）")

    # tap
    tp = sub.add_parser("tap", help="ADB 点击")
    tp.add_argument("--x", type=int, required=True)
    tp.add_argument("--y", type=int, required=True)

    args = parser.parse_args()

    if args.cmd == "screenshot":
        cmd_screenshot(args)
    elif args.cmd == "swipe":
        cmd_swipe(args)
    elif args.cmd == "tap":
        cmd_tap(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
