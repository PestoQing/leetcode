#!/bin/bash
set -euo pipefail
cd /home/yimu/Desktop/leetcode/强化学习
exec systemd-run --user --scope -p CPUQuota=150% -p MemoryMax=6G -p MemorySwapMax=0 .venv/bin/python lab.py "$@"
