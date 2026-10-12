# 题目描述：
# 有 n 个节点的二叉树，根节点编号为 0，节点权值为 nums[i]。
# 使用 DFS 遍历整棵树。
# 如果一个节点有两个子节点 l、r：
# 先访问 l 的概率为 nums[l] / (nums[l] + nums[r])，
# 否则先访问 r。
#
# dfn[i] 是节点 i 的访问序号，从 1 开始。
# 满意度为所有 (n - dfn[i] + 1) * nums[i] 的总和。
# 可以将最多一个节点的权值改成 w，也可以不修改。
# 求最大的期望满意度。
#
# 输入：
# 第一行 n
# 接下来 n-1 个整数，为节点 1 到 n-1 的父节点编号
# 接下来 n 个整数，为各节点权值
# 最后一个整数 w，为修改后的权值
# 保证父节点编号小于子节点编号。
#
# 思路：
# 先计算子树大小 size 和子树权值和 sums。
# dp[i] 表示节点 i 的期望得分系数 E[n - dfn[i] + 1]。
# 修改一个节点只影响自身权值，以及它和兄弟节点的先后概率。
# 逐个计算修改收益，取最大值，无需为每个候选节点重新遍历整棵树。
# 这里 DFS 指先访问节点自身，再完整访问一个子树，最后访问另一个子树。
# 利用期望的线性性质，总期望 = 各节点权值乘以各自的期望得分系数之和。
# 时间复杂度 O(n)，空间复杂度 O(n)。
# 本实现要求原权值和修改后的权值能构成合法概率，且所有概率分母非零；
# 若题目允许两个兄弟的权值同时为 0，需要另行约定访问概率并处理。
#
# 测试 1 输入：
# 5
# 0 0 1 1
# 5 1 1 1 1
# 4
# 输出：
# 46.4000
#
# 测试 2 输入：
# 3
# 0 1
# 1 2 3
# 5
# 输出：
# 22.0000
#
# 测试 3 输入：
# 1
# 5
# 3
# 输出：
# 5.0000
# 说明：只有根节点，不修改更好。

import sys

# sys.stdin = open('input.txt', 'r')

# 输入由空白分隔，因此父节点列表、权值列表跨行也不影响解析。
data = sys.stdin.read().split()
n = int(data[0])

# 根节点没有父节点，用 -1 占位，使 parent[i] 与节点编号直接对应。
parent = [-1]
for i in range(n - 1):
    parent.append(int(data[1 + i]))

# data[0] 是 n，data[1:n] 是 n-1 个父节点，故权值从 data[n] 开始。
nums = []
for i in range(n):
    nums.append(int(data[n + i]))

# 最后一个权值位于 data[2*n-1]，其后就是统一的候选修改值 w。
w = int(data[2 * n])

# children[i]：节点 i 的子节点列表，二叉树中长度最多为 2。
children = []
# size[i]：以 i 为根的子树节点数，包含 i 自身。
size = []
# sums[i]：原始权值下，以 i 为根的子树权值总和。
sums = []

# 先让每个节点自成一棵子树，再建立父子关系并向上汇总。
for i in range(n):
    children.append([])
    size.append(1)
    sums.append(nums[i])

for i in range(1, n):
    children[parent[i]].append(i)

# 题目保证 parent[i] < i，因此逆序处理时，i 的所有后代都已经汇总完毕。
# 将 i 的完整子树信息累加到父节点，相当于后序遍历，不需要递归。
# 若没有“父编号小于子编号”的保证，就不能直接靠编号顺序计算。
for i in range(n - 1, 0, -1):
    p = parent[i]
    size[p] += size[i]
    sums[p] += sums[i]

# dp[i] = E[n-dfn[i]+1]：节点越早访问，得分系数越大。
# 根节点总是第 1 个访问，故 dp[0]=n，原始贡献为 n*nums[0]。
# 之后按编号追加 dp；父编号更小，计算子节点时父节点的 dp 已经存在。
dp = [n]
# res 累加完全不修改权值时的总期望满意度。
res = n * nums[0]

# best 保存“相对于原始总期望”的最大增量，每个候选均独立修改一个节点。
# 允许不修改，所以增量至少为 0。根节点无兄弟，其权值不影响子节点排序
# 概率，只改变自身得分，因此修改根节点的收益为 n*(w-nums[0])。
best = max(0, n * (w - nums[0]))

for i in range(1, n):
    p = parent[i]
    # change 可以为负：不能只根据权值增减判断收益，还要考虑访问顺序变化。
    change = w - nums[i]

    if len(children[p]) == 1:
        # 唯一子节点紧跟父节点访问，dfn 比父节点大 1，得分系数就小 1。
        # 修改 i 不改变任何分支概率，因此只有自身贡献变化。
        dp.append(dp[p] - 1)
        tmp = change * dp[i]
    else:
        # 找到兄弟节点
        j = children[p][0]
        if j == i:
            j = children[p][1]

        # 如果 i 先访问，dfn[i]=dfn[p]+1；如果 j 先访问，还需等整棵 j 子树。
        # j 先访问的概率为 nums[j]/(nums[i]+nums[j])，所以期望等待量
        # 是 size[j] 乘以该概率；得分系数随等待量增加而减少。
        dp.append(dp[p] - 1 - size[j] * nums[j] / (nums[i] + nums[j]))

        # 只有父节点 p 处选择 i、j 先后的概率会因修改 nums[i] 而改变。
        # 祖先的分支概率及 i 内部的分支概率依赖其他节点权值，均不受影响。
        # prob 为“修改后 i 先访问的概率 - 原先 i 先访问的概率”。
        prob = w / (w + nums[j]) - nums[i] / (nums[i] + nums[j])

        # 把总增量拆为两步，避免遗漏“新权值与新概率共同变化”的交叉项：
        # 1. 暂时保持原访问概率，仅修改自身权值，收益为 change*dp[i]。
        tmp = change * dp[i]
        # 2. 在修改后的权值下，再把 i 先访问的概率提高 prob。
        #    相比 j 先访问，i 子树的所有节点提前 size[j] 位，
        #    带来 size[j]*(sums[i]+change) 的收益；
        #    j 子树的所有节点推迟 size[i] 位，损失 size[i]*sums[j]。
        #    两棵子树之外的节点位置不变，因为这两棵子树的总大小不变。
        # 注意这里必须使用 sums[i]+change，而不是修改前的 sums[i]。
        tmp += prob * (size[j] * (sums[i] + change) - size[i] * sums[j])

    # dp、nums、sums 始终保留原始状态；各候选修改互不叠加。
    # 先累计当前节点的原始期望贡献，再更新最佳单点修改收益。
    res += dp[i] * nums[i]
    best = max(best, tmp)

# 原始期望加最佳增量即为答案，按题意保留四位小数。
print(f"{res + best:.4f}")