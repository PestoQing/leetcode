import sys
import heapq

# sys.stdin = open('input.txt', 'r')


def estimate(x, y, b1, b2):
    dx = abs(x - b1)
    dy = abs(y - b2)
    # 一步在单个方向最多移动 2，两方向的距离和最多减少 3。
    res = max((dx + 1) // 2, (dy + 1) // 2, (dx + dy + 2) // 3)
    # 每走一步，x+y 的奇偶性改变，因此步数的奇偶性也已确定。
    if res % 2 != (dx + dy) % 2:
        res += 1
    return res


data = sys.stdin.read().split()
n = int(data[0])
index = 1
ans = []
direction = [(1, 2), (1, -2), (-1, 2), (-1, -2),
             (2, 1), (2, -1), (-2, 1), (-2, -1)]

for i in range(n):
    a1 = int(data[index])
    a2 = int(data[index + 1])
    b1 = int(data[index + 2])
    b2 = int(data[index + 3])
    index += 4

    # dist 保存已找到的最少步数，发现更短路径时更新。
    dist = {(a1, a2): 0}
    h = estimate(a1, a2, b1, b2)
    # 堆按“已走步数 + 剩余估计”排序，同分时优先剩余估计小的点。
    queue = [(h, h, 0, a1, a2)]

    while queue:
        total, h, step, x, y = heapq.heappop(queue)
        if step != dist[(x, y)]:
            continue

        # 估计不超过真实剩余步数，目标出堆时得到最短路。
        if x == b1 and y == b2:
            ans.append(str(step))
            break

        for dx, dy in direction:
            next_x = x + dx
            next_y = y + dy
            if next_x < 1 or next_x > 1000 or next_y < 1 or next_y > 1000:
                continue

            cur = (next_x, next_y)
            if cur not in dist or step + 1 < dist[cur]:
                dist[cur] = step + 1
                h = estimate(next_x, next_y, b1, b2)
                heapq.heappush(queue, (step + 1 + h, h, step + 1, next_x, next_y))

print('\n'.join(ans))


# 思路
# 1. 把每个格子看成一个节点，骑士的八种移动对应八条可能的边，每条边花费 1 步。
# 2. 使用 A* 搜索。step 是已经走的步数，h 是到终点至少还需要的步数估计。
#    优先处理 step+h 最小的格子；同分时优先 h 小的格子，减少无效扩展。
# 3. dist[(x, y)] 保存目前找到的最少步数。发现更短路径时更新并重新入堆。
# 4. 每次检查棋盘边界；目标格子从堆中取出时，step 就是答案。
#
# 常见问题
# 1. 为什么不用普通 BFS？
#    每条边的代价都是 1，BFS 也能求最短路，写法更简单。
#    但棋盘有 100 万个格子，最多 100 组数据；A* 利用目标位置，通常搜索更少。
#
# 2. estimate 中的公式是什么意思，为什么不会高估？
#    一步在 x 或 y 方向最多移动 2，所以至少需要 ceil(dx/2)、ceil(dy/2) 步。
#    一步最多让 dx+dy 减少 3，所以还至少需要 ceil((dx+dy)/3) 步。
#    三个条件必须同时满足，因此取最大值；(dx+1)//2 就是向上取整。
#    每一步都会改变 x+y 的奇偶性，所以总步数必须与 dx+dy 同奇偶。
#    若估计值奇偶不符，就加 1；真实步数也必须满足这个条件，仍不会高估。
#    棋盘边界可能迫使骑士绕路，只会使真实最短路不小于这些下界。
#
# 3. 为什么目标出堆时才结束，而不是第一次发现目标就结束？
#    第一次发现目标只代表找到一条路径，其他待处理路径可能更短。
#    目标出堆时 h=0，且它的 step+h 最小；若还存在更短路径，
#    该路径上待处理节点的估计总步数会更小，应当先出堆，因此不会漏掉更短路径。
#
# 4. 为什么同一个格子可以重复入堆，还要检查 step != dist[(x, y)]？
#    先找到的路径可能较长，之后找到更短路径时需要更新。
#    heapq 不直接修改旧条目，所以把新条目压入堆，旧条目出堆时跳过。
#    heappush 是入堆，heappop 取出最小项；元组按从左到右的字段比较。
#
# 5. 时间和空间复杂度是多少？
#    设棋盘格子数为 V，每个格子最多连接 8 个邻居，所以边数 E=O(V)。
#    本题的估计满足 h(当前格) <= 1+h(邻居)，称为一致性：
#    邻居的估计加 1 已满足当前格的三个距离下界和奇偶条件。
#    因此一个格子以当前最短距离出堆后，不会再被更短路径重新扩展。
#    单组最坏时间 O(V log V)，辅助空间 O(V)，并不保证每组都只搜很少的点。
#    n 组最坏时间 O(n*V log V)；每组重新建立搜索数据，不同时保存 n 张棋盘。
#    计入输入 data 和输出 ans 的存储后，总空间为 O(V+n)。
#
# 6. 起终点相同、位于边角时怎么处理？
#    起终点相同时，起点第一次出堆就输出 0。
#    边角处仍枚举八种移动，但跳过坐标不在 [1, 1000] 内的位置。
#    不能直接把 estimate 当答案，例如 (1,1) 到 (2,2) 的估计是 2，实际需要 4 步。
