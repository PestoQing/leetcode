from math import sqrt
import sys
while True:
    # 读取本地数据
    # sys.stdin = open('input.txt', 'r')
    # 按行读取数据,两个以上
    n, m = map(int, input().split())
    # 按行读取数据，单个
    n = int(input())
    # 读取全部数据
    data = sys.stdin.read().split()
    # 另一种读取全部的方式
    input = sys.stdin.read
    data = input().split()
    total = n
    tmp = n
    for _ in range(m - 1):
        tmp = sqrt(tmp)
        total += tmp
    print(f"{total:.2f}")