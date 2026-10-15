"""用无头 Edge 自检演示页面，并截图。

检查项（引擎内置 #check 模式逐步遍历所有步骤）：
  - 遍历所有预设输入的所有步骤
  - 文字之间互相重叠、元素（含选中光环）遮挡文字
  - 左侧动画区在视口内需要上下滚动的像素
  - 代码区是否出现横向滚动
视口：2400x1180 ≈ 1920x1080 屏幕 80% 缩放；1920x940 ≈ 100% 缩放。

用法: python check.py <演示.html> [截图步骤 ...]
截图步骤可写成 N（当前默认输入第 N 步）或 P@N（第 P 个预设、从 0 计，的第 N 步）。
截图默认取中间一步和最后一步，输出到系统临时目录 algoviz-shots/。
"""
import html as htmlmod
import json
import os
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
import tempfile

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/microsoft-edge", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]
VIEWS = [(2400, 1180, "80% 缩放"), (1920, 940, "100% 缩放")]

edge = next((p for p in EDGE_CANDIDATES if os.path.exists(p)), None)
if not edge:
    sys.exit("未找到 Edge / Chrome")

page = pathlib.Path(sys.argv[1]).resolve()
url = page.as_uri()
tmp = pathlib.Path(tempfile.gettempdir()) / "algoviz-shots"
tmp.mkdir(exist_ok=True)
profile = tmp / "profile"


def run(args):
    base = [edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            f"--user-data-dir={profile}", "--virtual-time-budget=6000"]
    return subprocess.run(base + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


ok = True
steps_total = None
for w, h, name in VIEWS:
    out = run([f"--window-size={w},{h}", "--dump-dom", url + "#check"]).stdout
    m = re.search(r'<pre id="av-check">(.*?)</pre>', out, re.S)
    if not m or not m.group(1).strip():
        print(f"[{name}] 未得到自检结果（页面脚本可能报错）")
        ok = False
        continue
    r = json.loads(htmlmod.unescape(m.group(1)))
    steps_total = r["lastSteps"]
    bad = r["leftNeedsScroll"] > 0 or r["codeHScroll"] > 0 or r["overlapCount"] > 0
    ok &= not bad
    print(f"[{name} {w}x{h}] {'FAIL' if bad else 'OK'}  总步骤数(全部预设)={r['steps']}  左侧需滚动={r['leftNeedsScroll']}px  "
          f"代码横向滚动={r['codeHScroll']}px  遮挡={r['overlapCount']}")
    for o in r["overlaps"][:15]:
        print(f"    {o['step']}: {o['type']}  「{o['a']}」 x 「{o['b']}」")

shots = sys.argv[2:] or ([str(steps_total // 2), str(steps_total - 1)] if steps_total else ["0"])
for s in shots:
    pre, _, st = s.rpartition("@")
    f = tmp / f"{page.stem}-{'p' + pre + '-' if pre else ''}step{st}.png"
    run(["--window-size=2400,1180", f"--screenshot={f}", url + (f"#preset={pre}&step={st}" if pre else f"#step={st}")])
    print("截图:", f)
sys.exit(0 if ok else 1)
