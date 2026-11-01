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

edges = []
index = 2
for i in range(m):
    a = int(data[index])
    b = int(data[index + 1])
    v = int(data[index + 2])
    # 把权值放在第一项，直接 sort 就会优先按权值排序。
    edges.append((v, a, b))
    index += 3
edges.sort()

parent = []
size = []
for i in range(n + 1):
    parent.append(i)
    size.append(1)


def find(x):
    root = x
    while parent[root] != root:
        root = parent[root]
    # 路径压缩：沿途节点直接指向根，方便后续查询。
    while parent[x] != x:
        next_node = parent[x]
        parent[x] = root
        x = next_node
    return root


res = 0
cnt = 0
for v, a, b in edges:
    root_a = find(a)
    root_b = find(b)
    if root_a == root_b:
        continue

    # 小连通块接到大连通块下面，控制并查集树的高度。
    if size[root_a] < size[root_b]:
        tmp = root_a
        root_a = root_b
        root_b = tmp
    parent[root_b] = root_a
    size[root_a] += size[root_b]
    res += v
    cnt += 1
    if cnt == n - 1:
        break

if cnt == n - 1:
    print(res)
else:
    # 题面未规定不连通图的输出，这里额外约定为 -1。
    print(-1)


# 思路
# Kruskal 按边权从小到大枚举道路，只有两个端点属于不同连通块时才选入。
# 并查集 parent 表示父节点；find 找根并压缩路径，根相同说明两点已经连通。
# 合并两个连通块并累计边权，选够 n-1 条边就得到最小生成树。
#
# 常见问题
# 1. 为什么不能直接取最便宜的 n-1 条边？
#    这些边可能成环、漏掉其他岛屿，所以要用并查集检查端点是否已经连通。
# 2. 为什么两点根相同就跳过？
#    两点已经有一条树内路径，再连一条边会成环；自环也会在这里跳过。
# 3. 排序后的每项是什么？
#    (v,a,b) 先按权值v排序，同权时依次比较a和b，方便稳定演示和复现。
# 4. size 的作用是什么？
#    仅根节点的 size 表示连通块大小；将小树挂到大树下，配合路径压缩加快查找。
#    非根节点的 size 不再代表当前整个连通块的大小。
# 5. 时间与空间复杂度？
#    排序 O(m log m)，并查集操作均摊 O(m*α(n))，初始化 O(n)。
#    总时间 O(n+m log m+m*α(n))，空间 O(n+m)，α(n) 是增长极慢的反阿克曼函数。
# 6. 重边、同权边、负权边和不连通情况？
#    重边分别参与排序，已连通后自动跳过；支持零权和负权，同权可有多棵最优树。
#    单个岛屿输出0；不连通时选不够 n-1 条边，这里额外约定输出-1。


# 以下为修改前的 Prim 代码，完整注释保留。
# import sys
#
# # sys.stdin = open('input.txt', 'r')
#
# data = sys.stdin.read().split()
# n = int(data[0])
# m = int(data[1])
# inf = float('inf')
#
# grid = []
# for i in range(n + 1):
#     row = []
#     for j in range(n + 1):
#         row.append(inf)
#     grid.append(row)
#
# index = 2
# for i in range(m):
#     a = int(data[index])
#     b = int(data[index + 1])
#     v = int(data[index + 2])
#     # 无向图写两个方向，重边只保留较小权值。
#     # grid[a][b] = min(grid[a][b], v)
#     # grid[b][a] = min(grid[b][a], v)
#     grid[a][b] = v
#     grid[b][a] = v
#     index += 3
#
# dist = []
# seen = []
# for i in range(n + 1):
#     dist.append(inf)
#     seen.append(False)
#
# # dist[i] 是将岛屿 i 接入当前生成树所需的最小边权。
# dist[1] = 0
# res = 0
# for i in range(n):
#     cur = -1
#     for j in range(1, n + 1):
#         if seen[j]:
#             continue
#         # 还没有候选，或当前岛屿的接入成本更小，就更新 cur。
#         # cur==-1 时 or 短路，不会读取 dist[-1]。
#         if cur == -1 or dist[j] < dist[cur]:
#             cur = j
#
#     # 没有候选，或候选仍不可达，说明无法连接全部岛屿。
#     if cur == -1 or dist[cur] == inf:
#         res = -1
#         break
#
#     seen[cur] = True
#     res += dist[cur]
#     for j in range(1, n + 1):
#         if not seen[j]:
#             dist[j] = min(dist[j], grid[cur][j])
#
# print(res)
#
#
# # 思路
# # 本题要求连接所有岛屿的总边权最小，是最小生成树问题。
# # Prim 从岛屿1开始，每次选择接入当前树成本最小的未加入岛屿。
# # 将它加入树并累计对应边权，再用它的出边更新其他岛屿的接入成本。
# # 起点的 dist[1]=0，只是为了让它首先被选中，不会多算一条边。
# #
# # 常见问题
# # 1. dist 和 Dijkstra 中的距离有什么区别？
# #    这里 dist[j] 是岛屿 j 到当前树的最小连接边权，不是起点到 j 的路径长度。
# #    因此更新用 grid[cur][j]，不能加上 dist[cur]。
# # 2. 为什么每次选最小连接边是正确的？
# #    当前树内外形成一个割，跨越这个割的最小边可以属于某棵最小生成树。
# #    每次选这样的安全边，不会失去最优解。
# # 3. 为什么不产生环？
# #    每次只把一个尚未加入树的岛屿接进来，不连接两个已经在树内的点。
# # 4. 时间和空间复杂度是多少？
# #    建矩阵 O(n²)，读取道路 O(m)，n轮中各进行两次 O(n) 扫描。
# #    总时间 O(n²+m)；不计输入token的空间 O(n²)，计入后 O(n²+m)。
# # 5. 重边、同权边、负权边、自环怎么处理？
# #    重边取最小值，同权时可以任取一条，生成树可能不同但最小总权值不变。
# #    Prim 支持零权和负权；更新只考虑未加入的岛屿，自环不会被选中。
# # 6. 如果只有一个岛屿，或者图不连通呢？
# #    单岛屿无需建路，输出0。
# #    不连通时不存在生成树；题面未规定此时输出，本实现额外约定输出-1。
#
#
# # 原使用 best 的选点写法，完整注释保留：
# # for i in range(n):
# #     cur = -1
# #     best = inf
# #     for j in range(1, n + 1):
# #         if not seen[j] and dist[j] < best:
# #             best = dist[j]
# #             cur = j
# #
# #     # 没有可接入的岛屿，说明图不连通，不存在生成树。
# #     if cur == -1:
# #         res = -1
# #         break
# #
# #     seen[cur] = True
# #     res += best
# #     for j in range(1, n + 1):
# #         if not seen[j]:
# #             dist[j] = min(dist[j], grid[cur][j])
