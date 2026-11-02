#!/bin/bash
set -euo pipefail
PROJECT='/home/yimu/Desktop/leetcode/强化学习'
URL='http://127.0.0.1:8765/'
UNIT='rl-lab-teaching.service'
cd "$PROJECT"
if curl --noproxy '*' -fsS --max-time 2 "${URL}api/live/status" 2>/dev/null | grep '"available": true' >/dev/null; then
    printf '逐轮教学服务已启动：%s\n' "$URL"
else
    # 只替换本项目的旧静态服务，不关闭其他已授权仿真或训练进程。
    if systemctl --user is-active --quiet "$UNIT"; then
        current=$(systemctl --user show "$UNIT" -p ExecStart --value)
        if [[ "$current" != *"$PROJECT"* ]]; then
            printf '同名服务不属于本项目，请检查。\n' >&2; exit 1
        fi
        systemctl --user stop "$UNIT"
    fi
    if curl --noproxy '*' -s --max-time 1 "$URL" >/dev/null 2>&1; then
        printf '8765端口被其他服务占用，请检查。\n' >&2; exit 1
    fi
    # 一个服务共享总限额；训练线程串行，不为每个实验另开一份资源预算。
    systemd-run --user --unit=rl-lab-teaching --collect \
        -p CPUQuota=150% -p MemoryHigh=4G -p MemoryMax=6G -p MemorySwapMax=0 -p TasksMax=128 \
        -p KillMode=control-group \
        "$PROJECT/.venv/bin/python" "$PROJECT/teaching_server.py"
    ready=0
    for i in {1..100}; do
        if curl --noproxy '*' -fsS --max-time 1 "${URL}api/live/status" >/dev/null 2>&1; then ready=1; break; fi
        sleep .1
    done
    if [ "$ready" -eq 0 ]; then printf '启动失败，运行 journalctl --user -u rl-lab-teaching 查看日志。\n' >&2; exit 1; fi
    printf '逐轮教学服务已启动：%s\n' "$URL"
fi
if command -v xdg-open >/dev/null; then xdg-open "$URL" >/dev/null 2>&1 & fi
