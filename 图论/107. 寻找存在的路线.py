# 题目描述
# 给定一个包含 n 个节点的无向图中，节点编号从 1 到 n （含 1 和 n ）。



# 你的任务是判断是否有一条从节点 source 出发到节点 destination 的路径存在。

# 输入描述
# 第一行包含两个正整数 N 和 M，N 代表节点的个数，M 代表边的个数。 

# 后续 M 行，每行两个正整数 s 和 t，代表从节点 s 与节点 t 之间有一条边。 

# 最后一行包含两个正整数，代表起始节点 source 和目标节点 destination。

# 输出描述
# 输出一个整数，代表是否存在从节点 source 到节点 destination 的路径。如果存在，输出 1；否则，输出 0。

# 输入示例
# 5 4
# 1 2
# 1 3
# 2 4
# 3 4
# 1 4
# 输出示例：1

# 思路：每条无向边把两个节点所在的集合连接起来。
# parent[i] 保存并查集中的父节点编号，不代表原图里一定有这条边。
# parent[i] == i 时，i 是集合的根（代表节点）。同根就代表存在路径。
# size[root] 记录根所代表的集合大小，只有根节点的 size 有效。
# 路径压缩 + 按大小合并，均摊时间 O((n+m) * α(n))，空间 O(n)。

import sys

# 本地读取 input.txt；提交在线评测时注释掉下一行。
sys.stdin = open('input.txt', 'r')
n, m = map(int, input().split())

# 下标 0 占位。最初每个节点独立成集合，父节点是自己，大小为 1。
parent = [0]
size = [0]
for i in range(1, n + 1):
    parent.append(i)
    size.append(1)


def find(x):
    # 第一趟：沿父指针一直向上，找到“父节点等于自己”的根。
    root = x
    while parent[root] != root:
        root = parent[root]

    # 第二趟：让沿途节点直接指向根，使以后的查找更快。
    # 必须先保存旧父节点，否则改写 parent[x] 后会丢失继续向上的位置。
    while parent[x] != x:
        next_node = parent[x]
        parent[x] = root
        x = next_node

    return root


for i in range(m):
    s, t = map(int, input().split())
    root_s = find(s)
    root_t = find(t)

    # 已经属于同一个集合：包括重复边、自环和成环边，都不需要再次合并。
    if root_s == root_t:
        continue

    # 让 root_s 代表较大的集合，把较小的集合挂到它下面，避免树变得太高。
    if size[root_s] < size[root_t]:
        root_s, root_t = root_t, root_s

    parent[root_t] = root_s
    size[root_s] += size[root_t]
    # root_t 已不是根，size[root_t] 不再表示有效的集合大小。

source, destination = map(int, input().split())
source_root = find(source)
destination_root = find(destination)

# 根相同就说明两个节点属于同一连通分量，即存在路径。
# source == destination 时，即使没有任何边，也存在长度为 0 的路径。
if source_root == destination_root:
    print(1)
else:
    print(0)
