"""修改Python后执行此脚本，同步index.html使用的代码片段、行号与完整中文源码。

保留手写课程和互动逻辑，只替换标记后的生成内容，避免源码与教学页面脱节。
算法行为变化时，还需同步检查il-bridges.js、live.js中的公式与解说。
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
file=ROOT/'教学资源/course.js'
text=file.read_text()
marker='// BEGIN GENERATED SOURCE SNAPSHOTS'
if marker in text:text=text[:text.index(marker)]

def section(filename,start,end):
    lines=(ROOT/filename).read_text().splitlines()
    a=next(i for i,s in enumerate(lines) if start in s)
    b=next((i for i in range(a+1,len(lines)) if end in lines[i]),len(lines))
    return dict(file=filename,start=a+1,text='\n'.join(f'{i+1:3}  {lines[i]}' for i in range(a,b)))

sources={
    'entry':section('lab.py','def main():','    if a.command=='),
    'data':section('lab.py',"    elif a.command=='collect':","    elif a.command=='evaluate':"),
    'bc':section('lab.py','            for step in range(a.steps):','        (out/\'config.json\')'),
    'iql':section('live_engine.py','    def offline_update(self):','    def sac_update(self):'),
    'ppo':section('live_engine.py','    def ppo_update(self):','    def offline_update(self):'),
    'sac':section('live_engine.py','    def sac_update(self):','    def update(self):'),
    'evaluation':section('lab.py',"    elif a.command=='evaluate':",'    else:')
}
full={name:(ROOT/name).read_text() for name in ['lab.py','live_engine.py','teaching_server.py']}
results={}
for p in (ROOT/'runs').glob('*/evaluation.json'):
    results[p.parent.name]=json.loads(p.read_text())
file.write_text(text+marker+'\nconst SOURCES='+json.dumps(sources,ensure_ascii=False)+';\nconst ANNOTATED_SOURCES='+json.dumps(full,ensure_ascii=False)+';\nconst EXISTING_RESULTS='+json.dumps(results,ensure_ascii=False)+';\n')
print('网页片段、行号和详细注释源码已同步。')
