# 题目描述
# 给定一个有向图，包含 N 个节点，节点编号分别为 1，2，...，N。现从 1 号节点开始，如果可以从 1 号节点的边可以到达任何节点，则输出 1，否则输出 -1。

# 输入描述
# 第一行包含两个正整数，表示节点数量 N 和边的数量 K。
# 后续 K 行，每行两个正整数 s 和 t，表示从 s 节点有一条边单向连接到 t 节点。

# 输出描述
# 如果可以从 1 号节点的边可以到达任何节点，则输出 1，否则输出 -1。

# 输入示例
# 4 4
# 1 2
# 2 1
# 1 3
# 2 4
# 输出示例：1

# 思路：只从节点 1 出发，沿有向边寻找所有能到达的节点。
# 最后检查 visited 中的节点数是否为 n；不是要求整张图强连通。
# 邻接矩阵写法的时间复杂度为 O(n^2 + k)，空间复杂度为 O(n^2)。

import sys
from collections import deque

# 与字符串迁移的代码一致，本地从 input.txt 读取；在线提交时注释掉下一行。
sys.stdin = open('input.txt', 'r')
n, k = map(int, input().split())

# 节点编号为 1 到 n；第 0 行、第 0 列占位，不参与遍历。
# graph[s][t] 为 1 表示存在 s -> t 的有向边；为 0 表示没有这条边。
graph = [[0] * (n + 1) for _ in range(n + 1)]
for i in range(k):
    s, t = map(int, input().split())
    graph[s][t] = 1
    # 有向边只写一个方向，不能同时设置 graph[t][s]。
    # 重复边重复赋值为 1，不影响结果；自环也能由 visited 避免重复访问。

# 集合保存已发现的节点编号，成员查询平均为 O(1)。
visited = set()

# 队列先进先出，先处理较早发现的节点，逐层向外搜索。
# 起点 1 自身也算能到达，因此先加入集合。
queue = deque([1])
visited.add(1)

while queue:
    current = queue.popleft()

    # 按编号从小到大检查 current 的所有可能邻居。
    # 队首先处理先入队的节点。
    for next_node in range(1, n + 1):
        # 两个条件必须同时成立，才发现一个新节点：
        # 1. graph[current][next_node] == 1：有从 current 指向 next_node 的边。
        # 2. next_node not in visited：该节点尚未被发现，避免重复加入。
        # and 从左到右短路：如果没有这条边，就不再检查集合成员。
        if graph[current][next_node] == 1 and next_node not in visited:
            # 在入队前立即标记。即使存在环，也不会无限重复访问。
            visited.add(next_node)
            queue.append(next_node)

# 队列为空时，从 1 能到达的节点已全部发现。
# n=1 且无边时，visited={1}，同样输出 1。
if len(visited) == n:
    print(1)
else:
    print(-1)
