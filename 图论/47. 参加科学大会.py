
# 小明是一位科学家，他需要参加一场重要的国际科学大会，以展示自己的最新研究成果。

# 小明的起点是第一个车站，终点是最后一个车站。然而，途中的各个车站之间的道路状况、交通拥堵程度以及可能的自然因素（如天气变化）等不同，这些因素都会影响每条路径的通行时间。

# 小明希望能选择一条花费时间最少的路线，以确保他能够尽快到达目的地。

# 输入描述
# 第一行包含两个正整数，第一个正整数 N 表示一共有 N 个公共汽车站，第二个正整数 M 表示有 M 条公路。 

# 接下来为 M 行，每行包括三个整数，S、E 和 V，代表了从 S 车站可以单向直达 E 车站，并且需要花费 V 单位的时间。

# 输出描述
# 输出一个整数，代表小明从起点到终点所花费的最小时间。

import sys

def dijkstra(n, m, edges, start, end):
    # 初始化邻接矩阵：对角线为 0（原地停留不耗时），其他位置为无穷大。
    grid = [[float('inf')] * (n + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        grid[i][i] = 0

    for p1, p2, val in edges:
        # 边权非负，走自环不会优于原地停留，因此保持对角线为 0。
        if p1 == p2:
            continue
        grid[p1][p2] = val

    # 初始化距离数组和访问数组
    minDist = [float('inf')] * (n + 1)
    visited = [False] * (n + 1)

    minDist[start] = 0  # 起始点到自身的距离为0

    for _ in range(1, n + 1):  # 遍历所有节点
        minVal = float('inf')
        cur = -1

        # 从尚未确定最短距离的节点中，选出当前距离起点（1 号车站）最近的节点
        for v in range(1, n + 1):
            # 同时满足：v 的最短距离尚未确定，且比当前候选节点更近。
            if not visited[v] and minDist[v] < minVal:
                minVal = minDist[v]
                cur = v

        if cur == -1:  # 如果找不到未访问过的节点，提前结束
            break

        visited[cur] = True  # 标记该节点已被访问

        # 尝试经由当前节点 cur，缩短从起点（1 号车站）到其他未确定节点的距离
        for v in range(1, n + 1):
            # 三个条件必须同时成立，才进行“松弛”（更新更短的距离）：
            # 1. not visited[v]：v 的最短距离尚未确定，仍有必要尝试更新。
            # 2. grid[cur][v] != inf：存在从 cur 指向 v 的直接道路。
            # 3. minDist[cur] + grid[cur][v] < minDist[v]：
            #    从起点先到 cur，再沿直接道路到 v，比目前已知的到 v 路线更短。
            # and 从左到右短路判断：前面的条件不成立，后面的条件就不再计算。
            if not visited[v] and grid[cur][v] != float('inf') and minDist[cur] + grid[cur][v] < minDist[v]:
                minDist[v] = minDist[cur] + grid[cur][v]

    return -1 if minDist[end] == float('inf') else minDist[end]

input = sys.stdin.read
data = input().split()
n, m = int(data[0]), int(data[1])
edges = []
index = 2
for _ in range(m):
    p1 = int(data[index])
    p2 = int(data[index + 1])
    val = int(data[index + 2])
    edges.append((p1, p2, val))
    index += 3
start = 1  # 起点
end = n    # 终点

result = dijkstra(n, m, edges, start, end)
print(result)