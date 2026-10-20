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
# 先用三维 Floyd 求最短路，再用集合与字典 DP 求最短访问路线。
# 通行时间按非负数理解；本实现适用于 n >= 1、k >= 1 的输入。
# 状态数量仍可能指数增长；使用集合和字典主要是让状态含义更直观。
# 考虑集合复制与哈希的 O(n) 开销，时间上界 O(n^3 + n^3 * 2^(n-1))，
# 空间上界 O(n^3 + n^2 * 2^(n-1))。只保留相邻两轮的可达状态。
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

# floyd[i][j][t]：只允许编号 0 到 t-1 的点作为中间点时，
# 从 i 到 j 的最短距离。第三维 t 是阶段，范围为 0 到 n。
# 输入中的 k 是配送员数量，因此用 t 表示 Floyd 阶段，避免混淆。
# t=0 不允许任何中间点，只能走直接道路；正无穷表示不可达。
inf = float('inf')
floyd = [
    [[inf] * (n + 1) for j in range(n)]
    for i in range(n)
]
for i in range(n):
    floyd[i][i][0] = 0

index = 3
for i in range(m):
    # 输入从 1 编号，数组从 0 编号，所以仓库对应数组中的点 0。
    u = int(data[index]) - 1
    v = int(data[index + 1]) - 1
    w = int(data[index + 2])
    index += 3

    # 双向道路要更新两个方向；重边仅保留耗时最短的一条。
    floyd[u][v][0] = min(floyd[u][v][0], w)
    floyd[v][u][0] = min(floyd[v][u][0], w)

# 三维 Floyd：第 t 层新增允许点 t-1 作为中间点。
# 虽然 t 存在第三维，仍按 t 递增逐层计算，保证上一层已经全部完成。
# 最短路径可以途经任意点，包括仓库和其他配送员负责的点。
for t in range(1, n + 1):
    for i in range(n):
        for j in range(n):
            # 不经过新中间点：直接沿用上一层的最短距离。
            # 经过新中间点：拆成 i -> t-1 和 t-1 -> j，两段均取上一层。
            floyd[i][j][t] = min(
                floyd[i][j][t - 1],
                floyd[i][t - 1][t - 1] + floyd[t - 1][j][t - 1]
            )

# 固定第三维 t=n，取出允许全部点作为中间点的最终距离矩阵。
# 后面的集合与字典 DP 用它决定访问顺序；三维 Floyd 本身不解决访问顺序问题。
dist = [[floyd[i][j][n] for j in range(n)] for i in range(n)]

# 无向图中，只要有点无法从仓库到达，就不可能完成配送。
# 若所有点都与仓库连通，则每个点也都能返回仓库。
if inf in dist[0]:
    print(-1)
    sys.exit()

# 用集合直接表示已经纳入访问顺序的非仓库点，不再编码成二进制。
# dp[(visited, i)]：已纳入集合为 visited、停在点 i 时的最短时间。
# 同一个集合可能有不同的停留点，它们后续的通行成本不同，必须分别保存。
# 普通 set 可变，不能作为字典键；frozenset 是不可变集合，可以作为字典键。
# 例如 (frozenset({1, 3}), 3) 表示已经纳入点 1、3，当前停在点 3。
# 集合记录的是访问顺序中的点：某段最短路允许途经其他点，也允许重复经过。

# 起点：尚未纳入任何非仓库点，停在仓库 0，耗时为 0。
dp = {(frozenset(), 0): 0}

# 每轮加入一个新点，共加入 n-1 个非仓库点。
# dp 只存当前一轮的状态，next_dp 存下一轮，避免边遍历边修改字典。
for _ in range(n - 1):
    next_dp = {}

    for (visited, i), cost in dp.items():
        for j in range(1, n):
            # 用集合成员判断，已经纳入访问顺序的点不再加入。
            if j in visited:
                continue

            # 产生新集合，原来的 visited 不变，类型仍为 frozenset。
            new_visited = visited.union({j})
            state = (new_visited, j)
            new_cost = cost + dist[i][j]

            # 不同访问顺序可能到达相同的“集合 + 停留点”状态。
            # 字典中还没有这个状态时按无穷大处理，只保留最小耗时。
            if new_cost < next_dp.get(state, inf):
                next_dp[state] = new_cost

    dp = next_dp

# n-1 轮后，字典中的每个 visited 都包含全部非仓库点。
# 枚举最后停留点，再加上返回仓库的最短距离。
# n=1 时不进入上面的循环，初始状态直接得到 0 + dist[0][0] = 0。
res = inf
for (visited, i), cost in dp.items():
    res = min(res, cost + dist[i][0])

print(res)
