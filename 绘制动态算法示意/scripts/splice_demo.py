"""用 DEMO 样式与 DEMO 脚本替换演示 HTML 中的题目专用部分（ENGINE 部分保持不动）。

用法: python splice_demo.py <演示.html> <demo.css> <demo.js>
  demo.css 替换 <style> 中 "DEMO STYLE" 注释块之后到 </style> 的内容；
  demo.js  替换最后一个 <script> 中 "DEMO" 注释块之后的内容。
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

html_p, css_p, js_p = map(pathlib.Path, sys.argv[1:4])
html = html_p.read_text(encoding="utf-8")
css = css_p.read_text(encoding="utf-8").strip()
js = js_p.read_text(encoding="utf-8").strip()

style_pat = re.compile(r"(DEMO STYLE[^\n]*\n\s*=+\s*\*/\n)(.*?)(</style>)", re.S)
html, k1 = style_pat.subn(lambda m: m.group(1) + css + "\n" + m.group(3), html, count=1)
script_pat = re.compile(r"(<script>\s*/\* =+\s*\n\s*DEMO ——.*?=+\s*\*/\n)(.*?)(</script>\s*</body>)", re.S)
html, k2 = script_pat.subn(lambda m: m.group(1) + js + "\n" + m.group(3), html, count=1)
if k1 != 1 or k2 != 1:
    sys.exit(f"未找到 DEMO 区块（style={k1}, script={k2}）")
html_p.write_text(html, encoding="utf-8")
print(f"已替换 DEMO 部分 -> {html_p}")
