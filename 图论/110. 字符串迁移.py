def judge(s1,s2):
    count=0
    for i in range(len(s1)):
        if s1[i]!=s2[i]:
            count+=1
    return count==1


import sys
from collections import deque

sys.stdin = open('input.txt', 'r')
n=int(input())
beginstr,endstr=map(str,input().split())
if beginstr==endstr:
    # 序列只包含起点本身，因此字符串数为 1。
    print(1)
    exit()

# 节点 0 是起点，节点 1 至 n 是 strlist 中的字符串，节点 n + 1 是终点
# 收录所有字符串
strlist=[]
for i in range(n):
    strlist.append(input())

nodes = [beginstr] + strlist + [endstr]
node_count = n + 2

# 建立连接矩阵：两个字符串只相差一个字符时，表示两个节点相连
graph = [[0] * node_count for _ in range(node_count)]
for i in range(node_count):
    for j in range(i + 1, node_count):
        if judge(nodes[i], nodes[j]):
            graph[i][j] = 1
            graph[j][i] = 1

# 使用 BFS 搜索从节点 0 到节点 n + 1 的最短路径
visited = [False] * node_count
distance = [0] * node_count
queue = deque([0])
visited[0] = True

while queue:
    current = queue.popleft()
    if current == n + 1:
        # distance 记录迁移次数（边数），字符串数需要再加上起点。
        print(distance[current] + 1)
        break

    for next_node in range(node_count):
        # 两个条件必须同时成立，才发现并加入一个新的相邻节点：
        # 1. graph[current][next_node] == 1：两个字符串恰好相差一位，可以直接迁移。
        # 2. not visited[next_node]：这个节点以前没有被发现，避免重复入队。
        # and 从左到右短路判断：如果不相连，就不再检查第二个条件。
        if graph[current][next_node] == 1 and not visited[next_node]:
            visited[next_node] = True
            distance[next_node] = distance[current] + 1
            queue.append(next_node)
else:
    print(0)