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

# 最深递归链最多包含 n 个节点，为输入规模预留递归层数。
# 不再手动维护 stack 列表，但 Python 仍会使用函数调用栈保存每一层。
sys.setrecursionlimit(max(sys.getrecursionlimit(), n + 100))


def dfs(current):
    # 进入当前节点时立即标记，后续遇到环或重复边时会跳过它。
    visited.add(current)

    # 按编号从小到大查找邻居；找到一个就深入，返回后才继续找下一个。
    for next_node in range(1, n + 1):
        # 两个条件必须同时成立，才递归进入邻居：
        # 1. graph[current][next_node] == 1：存在 current -> next_node 的有向边。
        # 2. next_node not in visited：这个邻居还没有被发现。
        # and 从左到右短路：没有边时，就不会继续检查集合成员。
        if graph[current][next_node] == 1 and next_node not in visited:
            dfs(next_node)
            # 递归返回后，恢复本层的 current、next_node，继续本层循环。
            # 这里不要 visited.remove(next_node)：visited 记录全局已发现的点，
            # 不是当前路径。保留标记才能避免沿环反复搜索。

    # 所有邻居检查完，返回调用本函数的上一层。
    return


# 起点 1 自身也属于能到达的节点，在 dfs(1) 进入时会加入 visited。
dfs(1)

# 最外层 dfs(1) 返回后，从 1 能到达的节点已全部发现。
# n=1 且无边时，visited={1}，同样输出 1。
if len(visited) == n:
    print(1)
else:
    print(-1)
