# 题目描述
# 在世界的某个区域，有一些分散的神秘岛屿，每个岛屿上都有一种珍稀的资源或者宝藏。国王打算在这些岛屿上建公路，方便运输。

# 不同岛屿之间，路途距离不同，国王希望你可以规划建公路的方案，如何可以以最短的总公路距离将 所有岛屿联通起来（注意：这是一个无向图）。 

# 给定一张地图，其中包括了所有的岛屿，以及它们之间的距离。以最小化公路建设长度，确保可以链接到所有岛屿。

# 输入描述
# 第一行包含两个整数V 和 E，V代表顶点数，E代表边数 。顶点编号是从1到V。例如：V=2，一个有两个顶点，分别是1和2。

# 接下来共有 E 行，每行三个整数 v1，v2 和 val，v1 和 v2 为边的起点和终点，val代表边的权值。

# 输出描述
# 输出联通所有岛屿的最小路径总距离

# 输入示例
# 7 11
# 1 2 1
# 1 3 1
# 1 5 2
# 2 6 1
# 2 4 2
# 2 3 2
# 3 4 1
# 4 5 1
# 5 6 2
# 5 7 1
# 6 7 1
# 输出示例
# 6

import sys

# sys.stdin = open('input.txt', 'r')

data = sys.stdin.read().split()
n = int(data[0])
m = int(data[1])
inf = float('inf')

grid = []
for i in range(n + 1):
    row = []
    for j in range(n + 1):
        row.append(inf)
    grid.append(row)

index = 2
for i in range(m):
    a = int(data[index])
    b = int(data[index + 1])
    v = int(data[index + 2])
    # 无向图写两个方向，重边只保留较小权值。
    # grid[a][b] = min(grid[a][b], v)
    # grid[b][a] = min(grid[b][a], v)
    grid[a][b] = v
    grid[b][a] = v
    index += 3

dist = []
seen = []
for i in range(n + 1):
    dist.append(inf)
    seen.append(False)

# dist[i] 是将岛屿 i 接入当前生成树所需的最小边权。
dist[1] = 0
res = 0
for i in range(n):
    cur = -1
    for j in range(1, n + 1):
        if seen[j]:
            continue
        # 还没有候选，或当前岛屿的接入成本更小，就更新 cur。
        # cur==-1 时 or 短路，不会读取 dist[-1]。
        if cur == -1 or dist[j] < dist[cur]:
            cur = j

    # 没有候选，或候选仍不可达，说明无法连接全部岛屿。
    if cur == -1 or dist[cur] == inf:
        res = -1
        break

    seen[cur] = True
    res += dist[cur]
    for j in range(1, n + 1):
        if not seen[j]:
            dist[j] = min(dist[j], grid[cur][j])

print(res)


# 思路
# 本题要求连接所有岛屿的总边权最小，是最小生成树问题。
# Prim 从岛屿1开始，每次选择接入当前树成本最小的未加入岛屿。
# 将它加入树并累计对应边权，再用它的出边更新其他岛屿的接入成本。
# 起点的 dist[1]=0，只是为了让它首先被选中，不会多算一条边。
#
# 常见问题
# 1. dist 和 Dijkstra 中的距离有什么区别？
#    这里 dist[j] 是岛屿 j 到当前树的最小连接边权，不是起点到 j 的路径长度。
#    因此更新用 grid[cur][j]，不能加上 dist[cur]。
# 2. 为什么每次选最小连接边是正确的？
#    当前树内外形成一个割，跨越这个割的最小边可以属于某棵最小生成树。
#    每次选这样的安全边，不会失去最优解。
# 3. 为什么不产生环？
#    每次只把一个尚未加入树的岛屿接进来，不连接两个已经在树内的点。
# 4. 时间和空间复杂度是多少？
#    建矩阵 O(n²)，读取道路 O(m)，n轮中各进行两次 O(n) 扫描。
#    总时间 O(n²+m)；不计输入token的空间 O(n²)，计入后 O(n²+m)。
# 5. 重边、同权边、负权边、自环怎么处理？
#    重边取最小值，同权时可以任取一条，生成树可能不同但最小总权值不变。
#    Prim 支持零权和负权；更新只考虑未加入的岛屿，自环不会被选中。
# 6. 如果只有一个岛屿，或者图不连通呢？
#    单岛屿无需建路，输出0。
#    不连通时不存在生成树；题面未规定此时输出，本实现额外约定输出-1。


# 原使用 best 的选点写法，完整注释保留：
# for i in range(n):
#     cur = -1
#     best = inf
#     for j in range(1, n + 1):
#         if not seen[j] and dist[j] < best:
#             best = dist[j]
#             cur = j
#
#     # 没有可接入的岛屿，说明图不连通，不存在生成树。
#     if cur == -1:
#         res = -1
#         break
#
#     seen[cur] = True
#     res += best
#     for j in range(1, n + 1):
#         if not seen[j]:
#             dist[j] = min(dist[j], grid[cur][j])
