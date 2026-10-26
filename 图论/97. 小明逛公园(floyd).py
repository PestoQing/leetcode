# 题目描述
# 小明喜欢去公园散步，公园内布置了许多的景点，相互之间通过小路连接，小明希望在观看景点的同时，能够节省体力，走最短的路径。 



# 给定一个公园景点图，图中有 N 个景点（编号为 1 到 N），以及 M 条双向道路连接着这些景点。每条道路上行走的距离都是已知的。



# 小明有 Q 个观景计划，每个计划都有一个起点 start 和一个终点 end，表示他想从景点 start 前往景点 end。由于小明希望节省体力，他想知道每个观景计划中从起点到终点的最短路径长度。 请你帮助小明计算出每个观景计划的最短路径长度。

# 输入描述
# 第一行包含两个整数 N, M, 分别表示景点的数量和道路的数量。 

# 接下来的 M 行，每行包含三个整数 u, v, w，表示景点 u 和景点 v 之间有一条长度为 w 的双向道路。 

# 接下里的一行包含一个整数 Q，表示观景计划的数量。 

# 接下来的 Q 行，每行包含两个整数 start, end，表示一个观景计划的起点和终点。

# 输出描述
# 对于每个观景计划，输出一行表示从起点到终点的最短路径长度。如果两个景点之间不存在路径，则输出 -1。
import sys

# 本地调试时可以取消下一行注释，提交时直接读取标准输入。
sys.stdin = open('input.txt', 'r')

# 一次性读取输入并按空白切分，再按顺序解析景点、道路和查询。
data = sys.stdin.read().split()
n = int(data[0])  # 景点数量，编号为 1 到 n
m = int(data[1])  # 双向道路数量

inf = float('inf')

# dp[i][j][k]：只允许编号 1 到 k 的景点作为中间节点时，
# 从 i 到 j 的最短距离。起点 i 和终点 j 不受这个编号范围限制。
# 第一维 i 是起点，第二维 j 是终点，第三维 k 是允许的中间点编号上限。
# 保留所有 k 对应的状态，因此这是三维 Floyd，而非二维滚动优化。
dp = [
    [[inf] * (n + 1) for j in range(n + 1)]  # 每个 (i, j) 保存 k=0..n
    for i in range(n + 1)
]

# 第 0 层不允许经过任何中间节点，只能停留在原地或走一条直接道路。
for i in range(1, n + 1):
    dp[i][i][0] = 0

index = 2
for _ in range(m):
    u = int(data[index])
    v = int(data[index + 1])
    w = int(data[index + 2])
    index += 3

    # 双向道路更新两个方向；若同一对景点有多条道路，保留最短的一条。
    dp[u][v][0] = min(dp[u][v][0], w)
    dp[v][u][0] = min(dp[v][u][0], w)

# 虽然 k 存在数组第三维，计算仍按 k 从小到大逐层进行。
# 外层枚举 k，保证计算第 k 层时，第 k-1 层已经全部完成。
for k in range(1, n + 1):
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            # 情况一：不经过 k，沿用上一层从 i 到 j 的最短距离。
            # 情况二：经过 k，将路线拆成 i -> k 和 k -> j 两段。
            # 两段都取上一层的结果，保证其中间节点只来自 1 到 k-1。
            dp[i][j][k] = min(
                dp[i][j][k - 1],
                dp[i][k][k - 1] + dp[k][j][k - 1]
            )

q = int(data[index])
index += 1
answers = []

for _ in range(q):
    start = int(data[index])
    end = int(data[index + 1])
    index += 2

    # 第 n 层允许所有景点作为中间节点，保存最终的任意两点最短距离。
    distance = dp[start][end][n]
    answers.append(str(distance) if distance != inf else '-1')
print('\n'.join(answers))
print('\n')

# 时间复杂度：O(n^3 + m + q)；三维 DP 空间复杂度：O(n^3)。

