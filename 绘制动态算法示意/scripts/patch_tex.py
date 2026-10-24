"""给已生成的演示 HTML（以及模板）的 ENGINE 打上公式排版补丁：$…$ / $$…$$ 按 TeX 转 MathML。

用法: python patch_tex.py <演示.html> [...]
可重复执行：已有的公式排版代码块会被 tex_engine.js 的最新内容替换。
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).parent
BLOCK = HERE.joinpath("tex_engine.js").read_text(encoding="utf-8").rstrip() + "\n  // —— 公式排版结束\n"
CSS = (
    "/* 公式：MathML 按论文格式排版（数学字体、斜体变量、真正的上下标与分式） */\n"
    "math { font-family: 'Cambria Math', 'STIX Two Math', 'Latin Modern Math', math; font-size: 1.12em; }\n"
    "math[display=\"block\"] { margin: 2px 0; }\n"
    ".formula math { math-style: normal; }\n"
    ".stat .lab math, .card-h math, #inputs math, header math { font-size: 1em; }\n"
)


def sub1(pat, rep, s, name, flags=0, optional=False):
    s2, k = re.subn(pat, rep, s, count=1, flags=flags)
    if k != 1 and not optional:
        raise SystemExit(f"  ✗ 未找到：{name}")
    return s2


def patch(p):
    s = p.read_text(encoding="utf-8")
    # 1. 引擎代码块
    if "  // —— 公式排版：" in s:
        s = sub1(r"  // —— 公式排版：.*?  // —— 公式排版结束\n", lambda m: BLOCK, s, "旧公式块", re.S)
    else:
        s = sub1(r"(\n)(  return \{ \$, el, )", lambda m: m.group(1) + BLOCK + m.group(2), s, "AV 返回对象")
    # 2. 导出
    if "setHTML, tex:" not in s:
        s = sub1(r"(  return \{ \$, el, [^\n]*?)( \};\n\}\)\(\);)", lambda m: m.group(1) + ", setHTML, tex: TEX.convert, typeset: TEX.typeset" + m.group(2), s, "导出")
    # 3. setText 以原始串判断变化
    s = sub1(r"    if \(node\.textContent === t\) return false;\n    node\.textContent = t;\n",
             "    if ((node._raw != null ? node._raw : node.textContent) === t) return false;\n"
             "    node.textContent = t;\n"
             "    if (t.indexOf('$') >= 0) { node._raw = t; TEX.typeset(node); } else node._raw = null;\n",
             s, "setText", optional="node._raw != null" in s)
    # 4. 步骤说明 + render 结束同步排版
    s = sub1(r"if \(\$\('desc'\)\.innerHTML !== html\) \{ \$\('desc'\)\.innerHTML = html; ", "if (setHTML($('desc'), html)) { ", s, "desc", optional="setHTML($('desc')" in s)
    if "TEX.flush();" not in s:
        s = sub1(r"(\n    D\.render\(s, prev, data, P\);\n)", lambda m: m.group(1) + "    TEX.flush();\n", s, "render")
    # 5. 自检：公式整体当作一个文字块
    s = sub1(r"const host = node\.parentElement;\n(\s+)if \(host\.closest\('\.av-leaving",
             lambda m: "const host = node.parentElement.closest('math') || node.parentElement;\n" + m.group(1) + "if (host.closest('.av-leaving",
             s, "textRects", optional="closest('math') || node.parentElement" in s)
    if "seenMath" not in s:
        s = sub1(r"(    const range = document\.createRange\(\);\n)(\s+while \(w\.nextNode\(\)\) \{)",
                 lambda m: m.group(1) + "    const seenMath = new Set();\n" + m.group(2), s, "textRects seenMath")
        s = sub1(r"      range\.selectNodeContents\(node\);\n",
                 "      // 公式按整体外框参与检查（上下标、重音符的字形框会互相叠住，不算重叠）\n"
                 "      if (host.localName === 'math') { if (seenMath.has(host)) continue; seenMath.add(host); range.selectNode(host); }\n"
                 "      else range.selectNodeContents(node);\n", s, "textRects range")
        s = s.replace("out.push({ r, host, text: node.textContent.trim().slice(0, 16) });",
                      "out.push({ r, host, text: host.localName === 'math' ? host.textContent.trim().slice(0, 16) : node.textContent.trim().slice(0, 16) });")
    # 6. CSS
    if "math { font-family" not in s:
        s = sub1(r"(\n/\* =+\s*\n\s*DEMO STYLE)", lambda m: "\n" + CSS + m.group(1), s, "CSS")
    else:
        s = sub1(r"/\* 公式：MathML[^\n]*\n(?:[^\n]*math[^\n]*\n)+", lambda m: CSS, s, "CSS 更新")
    # 7. DEMO 里 “innerHTML 不同才写入” 的写法改为按原始串比较
    demo_at = s.find("DEMO ——")
    head, demo = s[:demo_at], s[demo_at:]
    demo, k1 = re.subn(r"if\s*\(([\w.$()'\[\]]+?)\.innerHTML\s*!==\s*([^)]+?)\)\s*\{\s*\1\.innerHTML\s*=\s*([^;]+?);\s*",
                       lambda m: f"if (AV.setHTML({m.group(1)}, {m.group(3)})) {{ ", demo)
    demo, k2 = re.subn(r"if\s*\(([\w.$()'\[\]]+?)\.innerHTML\s*!==\s*([^)]+?)\)\s*\1\.innerHTML\s*=\s*([^;]+?);",
                       lambda m: f"AV.setHTML({m.group(1)}, {m.group(3)});", demo)
    s = head + demo
    p.write_text(s, encoding="utf-8")
    print(f"  ✓ {p}（DEMO 写入点改写 {k1 + k2} 处）")


for a in sys.argv[1:]:
    patch(pathlib.Path(a))
