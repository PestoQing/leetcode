# 某国为促进城市间经济交流，决定对货物运输提供补贴。共有 n 个编号为 1 到 n 的城市，通过道路网络连接，网络中的道路仅允许从某个城市单向通行到另一个城市，不能反向通行。



# 网络中的道路都有各自的运输成本和政府补贴，道路的权值计算方式为：运输成本 - 政府补贴。权值为正表示扣除了政府补贴后运输货物仍需支付的费用；权值为负则表示政府的补贴超过了支出的运输成本，实际表现为运输过程中还能赚取一定的收益。



# 请找出从城市 1 到城市 n 的所有可能路径中，综合政府补贴后的最低运输成本。如果最低运输成本是一个负数，它表示在遵循最优路径的情况下，运输过程中反而能够实现盈利。



# 城市 1 到城市 n 之间可能会出现没有路径的情况，同时保证道路网络中不存在任何负权回路。

# 输入描述
# 第一行包含两个正整数，第一个正整数 n 表示该国一共有 n 个城市，第二个整数 m 表示这些城市中共有 m 条道路。 

# 接下来为 m 行，每行包括三个整数，s、t 和 v，表示 s 号城市运输货物到达 t 号城市，道路权值为 v （单向图）。

# 输出描述
# 如果能够从城市 1 到连通到城市 n， 请输出一个整数，表示运输成本。如果该整数是负数，则表示实现了盈利。如果从城市 1 没有路径可达城市 n，请输出 "unconnected"。

# 输入示例
# 6 7
# 5 6 -2
# 1 2 1
# 5 3 1
# 2 5 2
# 2 4 -3
# 4 6 4
# 1 3 5
# 输出示例
# 1

import sys

# sys.stdin = open('input.txt', 'r')

data = sys.stdin.read().split()
n = int(data[0])
m = int(data[1])
inf = float('inf')

# grid[s][t] 是 s 到 t 的直接道路权值，inf 表示没有这条边。
grid = []
for i in range(n + 1):
    row = []
    for j in range(n + 1):
        row.append(inf)
    grid.append(row)

index = 2
for i in range(m):
    s = int(data[index])
    t = int(data[index + 1])
    v = int(data[index + 2])
    # 单向边只写一个方向；同方向重边保留较小权值。
    grid[s][t] = min(grid[s][t], v)
    index += 3

dist = []
for i in range(n + 1):
    dist.append(inf)
dist[1] = 0

for i in range(n - 1):
    flag = False
    for s in range(1, n + 1):
        for t in range(1, n + 1):
            # 不可达或无边时，候选为 inf，不会小于已有距离。
            if dist[s] + grid[s][t] < dist[t]:
                dist[t] = dist[s] + grid[s][t]
                flag = True
    if not flag:
        break

if dist[n] == inf:
    print('unconnected')
else:
    print(dist[n])


# 思路
# 用二维邻接矩阵 grid 保存有向边，行是出发城市，列是到达城市。
# 没有直接道路用 inf，不能用 0，因为本题允许零权边和负权边。
# 每轮按城市编号依次扫描 s 和 t，用 dist[s]+grid[s][t] 尝试降低 dist[t]。
# dist 原地更新，同一轮的新距离可以继续传播；不是每轮只允许走一条边。
# 最多 n-1 轮，整轮没有更新时提前结束；本题保证不存在负权回路。
#
# 常见问题
# 1. 矩阵和边表有什么区别？
#    矩阵用 grid[s][t] 直接查询权值，但每轮最坏要扫描 n² 个位置。
#    边表只遍历 m 条实际道路，更适合稀疏图；这里按要求使用矩阵。
# 2. 为什么矩阵对角线不是默认 0？
#    grid 只存直接道路，未输入自环时对角线也是 inf。
#    起点到自身成本为0由 dist[1]=0表示，不需要虚构一条道路。
# 3. 重复边和单向边如何处理？
#    同方向多条边只保留最小权值，不会丢失更优路径。
#    写 grid[s][t] 不写 grid[t][s]，反向必须有单独输入的道路。
# 4. 为什么最多 n-1 轮？
#    无负权回路时，可去掉非负环，得到至多 n-1 条边的最短路径。
#    每轮至少能再传播一条边，因此 n-1 轮足够；传播顺序不影响最终答案。
# 5. 为什么不单独判断起点可达、道路存在？
#    float('inf') 加有限权值仍为 inf，inf 小于任何已有距离的判断都为 False。
#    没有边时权值也是 inf，所以一个比较就能涵盖这两种情况。
#    这里依赖真正的无穷大，不能直接换成任意一个有限的大整数。
# 6. 时间和空间复杂度？
#    初始化矩阵 O(n²)，读入 m 条道路 O(m)，最多 n-1 轮各扫描 n² 个位置。
#    最坏总时间 O(n³+m)，矩阵占 O(n²)，距离数组占 O(n)。
#    不计输入 token 存储时空间 O(n²)，计入 data 后总空间 O(n²+m)。


# 上一版较繁琐的判断，注释保留：
#         # 起点暂不可达时，跳过这一整行。
#         if dist[s] == inf:
#             continue
#         for t in range(1, n + 1):
#             # 先确认存在直接道路，再判断经过 s 能否降低到 t 的成本。
#             # and 短路：没有边时不计算后面的候选成本。
#             if grid[s][t] != inf and dist[s] + grid[s][t] < dist[t]:


# 以下为修改前的边表版本，完整注释保留，不参与执行。
# import sys
#
# # sys.stdin = open('input.txt', 'r')
#
# data = sys.stdin.read().split()
# n = int(data[0])
# m = int(data[1])
#
# edges = []
# index = 2
# for i in range(m):
#     s = int(data[index])
#     t = int(data[index + 1])
#     v = int(data[index + 2])
#     edges.append((s, t, v))
#     index += 3
#
# inf = float('inf')
# dist = []
# for i in range(n + 1):
#     dist.append(inf)
# dist[1] = 0
#
# # 没有负权回路，最短路径最多需要 n-1 条边。
# for i in range(n - 1):
#     flag = False
#     for s, t, v in edges:
#         # 先确认 s 可达，再判断经过 s 能否让 t 的成本更低。
#         if dist[s] != inf and dist[s] + v < dist[t]:
#             dist[t] = dist[s] + v
#             flag = True
#
#     # 整轮没有更新，说明所有距离已经稳定。
#     if not flag:
#         break
#
# if dist[n] == inf:
#     print('unconnected')
# else:
#     print(dist[n])
#
#
# # 思路
# # dist[i] 表示目前找到的从城市 1 到城市 i 的最低成本。
# # 起点成本为 0，其他城市先设为无穷大，表示暂时不可达。
# # 每轮遍历全部有向边 s -> t，尝试用 dist[s]+v 更新 dist[t]，这叫松弛。
# # 最多进行 n-1 轮；如果某轮没有更新，就提前结束。
# # 最后 dist[n] 为无穷大则不可达，否则输出最低成本。
# #
# # 常见问题
# # 1. 为什么使用 Bellman-Ford？
# #    本题允许负权边，普通 Dijkstra 的正确性条件不满足；Bellman-Ford 支持负权边。
# # 2. 为什么最多 n-1 轮？
# #    没有负权回路时，可去掉路径中的非负环，得到至多 n-1 条边的最短路径。
# #    每轮至少保证再推进一条边，因此 n-1 轮足够。
# # 3. 为什么先判断 dist[s] != inf？
# #    只有从起点能到达 s，才能通过 s -> t 更新起点到 t 的距离。
# #    and 从左到右判断；s 不可达时不会继续判断后面的表达式。
# # 4. 为什么可以原地更新，不复制上一轮 dist？
# #    本题不限制经过的边数，同轮更新可以继续传播，不影响最终最短距离。
# #    因此第 k 轮不一定只得到最多 k 条边的路径，也可能提前传播更远。
# #    若题目限制最多 k 条边，就应从上一轮副本读取，避免同轮连续传播。
# # 5. 时间和空间复杂度是多少？
# #    最坏松弛 n-1 轮，每轮 m 条边，连同初始化，时间 O(n*m+n+m)。
# #    通常将松弛部分记为 O(n*m)；dist 占 O(n)，边表占 O(m)。
# #    不计输入边表时辅助空间 O(n)；计入边表与 data 输入存储，总空间 O(n+m)。
# # 6. 需要额外判断负权回路吗？
# #    题目已保证没有负权回路，不需要额外检测。
# #    单向边只保存 s -> t；重边会分别参与松弛，不需要特别去重。
#
