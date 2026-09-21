from math import sqrt
import sys
while True:
    # 读取本地数据
    # sys.stdin = open('input.txt', 'r')
    # 按行读取数据
    n, m = map(int, input().split())
    # 读取全部数据
    data = sys.stdin.read().split()
    total = n
    tmp = n
    for _ in range(m - 1):
        tmp = sqrt(tmp)
        total += tmp
    print(f"{total:.2f}")