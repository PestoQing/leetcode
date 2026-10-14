"""把 .py 源码原样写入演示 HTML 的 <script type="text/plain" id="py-source"> 块。

用法: python embed_source.py <演示.html> <源码.py>
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

html_path, py_path = map(pathlib.Path, sys.argv[1:3])
html = html_path.read_text(encoding="utf-8")
src = py_path.read_text(encoding="utf-8").replace("</script", "<\/script")

pat = re.compile(r'(<script type="text/plain" id="py-source">)(.*?)(</script>)', re.S)
html, k = pat.subn(lambda m: m.group(1) + "\n" + src.rstrip() + "\n" + m.group(3), html, count=1)
if k != 1:
    sys.exit("未找到 py-source 块")
html_path.write_text(html, encoding="utf-8")
print(f"已嵌入 {py_path.name}（{src.count(chr(10)) + 1} 行）-> {html_path}")
