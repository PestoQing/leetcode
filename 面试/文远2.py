# 题目描述：
# 有 n 个点、m 条双向道路、k 个配送员，1 号点是仓库。
# 每个非仓库点必须恰好分配给一个配送员负责访问。
# 每个配送员从仓库出发，访问负责的所有点后回到仓库。
# 可以经过其他配送员负责的点，也可以多次经过仓库。
# 配送员可以不执行任务，耗时为 0。
# 求所有配送员的总通行时间最小值，无法覆盖所有点则输出 -1。
#
# 输入：
# 第一行 n m k
# 接下来 m 行，每行 u v w，表示双向道路及通行时间
# 两点间可能有重边，需要取最小值。
#
# 思路：
# 多个人的往返路线可以拼成一个人的路线，总时间不变。
# 反过来，让一个配送员完成整条路线，其他配送员休息，也符合要求。
# 所以在 k >= 1 时，多配送员和单配送员的最优总时间相等。
# 注意优化的是“总时间”；若要求最晚完成时间最小，就不能这样合并。
# 先用 Floyd 求最短路，再用状态压缩 DP 求最短访问路线。
# 通行时间按非负数理解；本实现适用于 n >= 1、k >= 1 的输入。
# 时间复杂度 O(n^3 + n^2 * 2^(n-1))。
# 空间复杂度 O(n^2 + n * 2^(n-1))，因此只适合节点数较少的情况。
#
# 测试 1 输入：
# 4 4 2
# 1 2 1
# 1 3 5
# 1 4 5
# 2 3 1
# 输出：
# 14
#
# 测试 2 输入：
# 3 1 1
# 1 2 4
# 输出：
# -1
#
# 测试 3 输入：
# 1 0 1
# 输出：
# 0

import sys

# sys.stdin = open('input.txt', 'r')

# 一次性读取所有输入；后面用 index 每次取出一条道路的三个字段。
data = sys.stdin.read().split()
n = int(data[0])
m = int(data[1])
k = int(data[2])

# dist[i][j] 保存两点之间的最短距离；初始只有自身到自身的距离为 0。
# 正无穷表示暂时不可达，便于直接进行 min 和加法运算。
inf = float('inf')
dist = []

for i in range(n):
    row = []
    for j in range(n):
        if i == j:
            row.append(0)
        else:
            row.append(inf)
    dist.append(row)

index = 3
for i in range(m):
    # 输入从 1 编号，数组从 0 编号，所以仓库对应数组中的点 0。
    u = int(data[index]) - 1
    v = int(data[index + 1]) - 1
    w = int(data[index + 2])
    index += 3

    # 双向道路要更新两个方向；重边仅保留耗时最短的一条。
    dist[u][v] = min(dist[u][v], w)
    dist[v][u] = min(dist[v][u], w)

# Floyd：依次允许点 t 作为中间节点，尝试用 i -> t -> j 改善 i -> j。
# t 必须在最外层，才能维护“只允许使用已经处理过的中间点”这一阶段含义。
# 最短路径可以途经任意点，包括仓库和其他配送员负责的点。
for t in range(n):
    for i in range(n):
        for j in range(n):
            dist[i][j] = min(dist[i][j], dist[i][t] + dist[t][j])

# 无向图中，只要有点无法从仓库到达，就不可能完成配送。
# 若所有点都与仓库连通，则每个点也都能返回仓库。
if inf in dist[0]:
    print(-1)
    sys.exit()

# mask 用 n-1 个二进制位记录已纳入访问顺序的非仓库点。
# 点 j 对应第 j-1 位：该位为 1 表示已纳入，为 0 表示尚未纳入。
# 例如 n=4 时，mask=0b101 表示点 1、3 已纳入，点 2 尚未纳入（数组编号）。
# dp[mask][i]：从仓库出发，已纳入集合为 mask，最后停在 i 的最小时间。
# 这里记录的是最短路压缩后的访问顺序：某段最短路可能已途经 mask 外的点，
# 不必立即给这些点置位，因为题目允许重复经过节点；后续仍可纳入访问顺序。
# 任意实际路线都可按各点首次出现顺序压缩，且用最短路替换各段不会更贵；
# 任意 DP 路线又能展开成合法实际路线，因此该建模不会改变最优值。
size = 2 ** (n - 1)
dp = []

for mask in range(size):
    row = []
    for i in range(n):
        row.append(inf)
    dp.append(row)

# 起点状态：尚未纳入任何非仓库点，停在仓库，累计耗时为 0。
dp[0][0] = 0

# 每次只添加一个未置位的点，新 mask 一定更大，按数值递增枚举即可。
for mask in range(size):
    for i in range(n):
        # 跳过不可达状态，避免无意义的转移。
        if dp[mask][i] == inf:
            continue

        for j in range(1, n):
            # 左移构造仅第 j-1 位为 1 的数，用于检测或设置点 j 的状态。
            bit = 1 << (j - 1)

            # 这个点已经访问过
            if mask & bit:
                continue

            # 按位或把点 j 加入集合，耗时增加从当前点 i 到 j 的最短路。
            # 同一个新状态可从不同的上一站到达，因此要取所有候选中的最小值。
            tmp = mask | bit
            dp[tmp][j] = min(dp[tmp][j], dp[mask][i] + dist[i][j])

# size-1 的低 n-1 位全为 1，表示所有非仓库点都已纳入访问顺序。
# 枚举最后停留点 i，加上返回仓库的最短距离，才是完整往返路线的耗时。
# n=1 时 size=1，直接得到 dp[0][0] + dist[0][0] = 0。
res = inf
for i in range(n):
    res = min(res, dp[size - 1][i] + dist[i][0])

print(res)