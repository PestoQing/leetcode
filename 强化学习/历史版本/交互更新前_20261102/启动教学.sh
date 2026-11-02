#!/bin/bash
set -euo pipefail
PROJECT='/home/yimu/Desktop/leetcode/强化学习'
URL='http://127.0.0.1:8765/'
cd "$PROJECT"
if curl --noproxy "*" -fsS --max-time 2 "$URL" 2>/dev/null | grep '强化学习 · 从模仿到探索' >/dev/null; then
    printf '教学网页已启动：%s\n' "$URL"
else
    if curl --noproxy "*" -s --max-time 2 "$URL" >/dev/null 2>&1; then
        printf '8765端口已被其他服务使用，请先检查。\n' >&2
        exit 1
    fi
    systemd-run --user --unit=rl-lab-teaching --collect \
        -p CPUQuota=30% -p MemoryMax=256M \
        "$PROJECT/.venv/bin/python" -m http.server 8765 --bind 127.0.0.1 --directory "$PROJECT"
    ready=0
    for i in {1..30}; do
        if curl --noproxy "*" -fsS --max-time 1 "$URL" >/dev/null 2>&1; then ready=1; break; fi
        sleep .1
    done
    if [ "$ready" -eq 0 ]; then printf '启动失败，请运行 journalctl --user -u rl-lab-teaching 检查日志。\n' >&2; exit 1; fi
    printf '教学网页已启动：%s\n' "$URL"
fi
if command -v xdg-open >/dev/null; then
    xdg-open "$URL" >/dev/null 2>&1 &
fi
