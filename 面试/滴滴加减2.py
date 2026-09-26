import sys

def solve():
    data = sys.stdin.read().split()
    if not data:
        return

    n = int(data[0])
    q = int(data[1])

    nums = [int(x) for x in data[2 : 2 + n]]
    asks = [int(x) for x in data[2 + n : 2 + n + q]]

    # 使用 append 动态构建数组，不需要一开始开好 MAX 大小的数组
    cnt = []
    sums = []
    odd = []

    # 1. 动态扩展并填充 nums 的信息
    for v in nums:
        # 如果当前数字超过了列表长度，动态 append(0) 扩展到足够长度
        while len(cnt) <= v:
            cnt.append(0)
            sums.append(0)
            odd.append(0)
            
        cnt[v] += 1
        sums[v] += v
        if v % 2 == 1:
            odd[v] += 1

    # 2. 确保查询需要用到的最大索引也存在（处理 x+1 越界问题）
    # 因为查询 x 可能比 nums 中的最大数字还要大
    max_x = max(asks) if asks else 0
    while len(cnt) <= max_x + 1:
        cnt.append(0)
        sums.append(0)
        odd.append(0)

    # 3. 动态计算前缀和
    for i in range(1, len(cnt)):
        cnt[i] += cnt[i - 1]
        sums[i] += sums[i - 1]
        odd[i] += odd[i - 1]

    # 相当于原代码中的 sums[MAX + 1]，现在直接用列表的最后一个元素
    total_cnt = cnt[-1]
    total_sum = sums[-1]
    total_odd = odd[-1]

    ans = []
    for x in asks:
        # --- 左侧部分：数值 <= x-1 ---
        if x >= 1:
            c1 = cnt[x - 1]
            s1 = sums[x - 1]
            o1 = odd[x - 1]
        else:
            c1 = s1 = o1 = 0

        # --- 右侧部分：数值 >= x+1 ---
        if x + 1 < len(cnt):
            c2 = total_cnt - cnt[x + 1]
            s2 = total_sum - sums[x + 1]
            o2 = total_odd - odd[x + 1]
        else:
            c2 = s2 = o2 = 0

        # --- 计算奇偶性冲突导致“多花一步”的数字个数 bad ---
        bad = 0
        if x % 2 == 0:
            bad = o1 + o2
        else:
            bad = (c1 - o1) + (c2 - o2)

        # --- 计算最小操作数 ---
        res = (abs(x * c1 - s1) + abs(x * c2 - s2) - bad) // 2
        ans.append(str(res))

    print(' '.join(ans))

if __name__ == '__main__':
    solve()

