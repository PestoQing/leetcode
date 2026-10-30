candidate = [(1, 1), (1, 1), (2, 2), (3, 0), (3, 4)]

# 带上原下标，先按 s 升序，再按 c 升序。
nums = []
for i in range(len(candidate)):
    nums.append((candidate[i][0], candidate[i][1], i))
nums.sort()

best = None
seen = set()
for s, c, index in nums:
    # 前面轨迹的 s 不大于当前 s；c 也不大于当前 c 时，当前轨迹排除。
    # 完全相同的轨迹只会保留最先出现的一条。
    if best is None or c < best:
        seen.add(index)
        best = c

res = []
for i in range(len(candidate)):
    if i in seen:
        res.append(candidate[i])
print(res)


# 思路
# 相同轨迹去重保留一条，再筛选没有被其他轨迹压过的轨迹。
# 按 (s,c,原下标) 排序后，前面轨迹的 s 一定不大于当前 s。
# best 记录前面轨迹的最小 c，当前 c >= best 就排除，否则保留并更新 best。
# 相同 (s,c) 中，原下标最小的一条先处理，其余重复项因 c == best 被排除。
# 最后按原下标输出，得到 [(1, 1), (3, 0)]。
#
# 常见问题
# 1. 两个 (1,1) 为什么只剩一个？
#    按用户最新确认，相同轨迹删除多余副本，保留第一条，不是两条同时删除。
# 2. 为什么 (3,0) 保留？
#    (1,1) 虽然 s 更小，但 c=1 大于 0，不能排除 (3,0)。
# 3. 为什么 (2,2)、(3,4) 被排除？
#    (1,1) 的两个指标都不大于它们，满足排除条件。
# 4. 时间和空间复杂度是多少？
#    排序 O(n log n)，扫描 O(n)，整体最坏 O(n log n)，额外空间 O(n)。
#    如果输入已经按 (s,c) 升序排列，省去排序后可以 O(n) 处理。
# 5. 会修改输入吗，输出顺序如何？
#    只排序新建的 nums，candidate 保持原样；结果按原输入顺序输出。


# 以下为修改前的完整文件，注释保留，不参与执行。
# candidate = ([1, 2], [2, 1], [1, 1], [3, 3])
#
# # 记录原下标，最后按输入顺序输出，不修改原始轨迹。
# nums = []
# for i in range(len(candidate)):
#     nums.append((candidate[i][0], candidate[i][1], i))
#
# # 每条记录是 (s, c, 原下标)，sort 按三个字段依次比较：
# # 先按 s 升序；s 相同才按 c 升序；s、c 都相同才按原下标升序。
# # 例如原轨迹 #2 为 (1, 1)，排序后位于 nums[0]=(1, 1, 2)。
# nums.sort()
#
# seen = set()
# best = None
# left = 0
# while left < len(nums):
#     # 同一个 s 的轨迹一起处理，找出最小 c 及其出现次数。
#     min_c = nums[left][1]
#     # left 是 nums 中的位置；index 是这条轨迹在原 candidate 中的位置。
#     # index 用来把排序后的候选对应回原数据，不是排序后的下标。
#     index = nums[left][2]
#     cnt = 1                # 组首已统计
#     right = left + 1        # 从下一条开始扫描
#     # 先确认 right 没有越界，再判断是否仍属于当前 s 分组；and 会短路。
#     while right < len(nums) and nums[right][0] == nums[left][0]:
#         if nums[right][1] < min_c:
#             min_c = nums[right][1]
#             cnt = 1
#             index = nums[right][2]
#         elif nums[right][1] == min_c:
#             cnt += 1
#         right += 1
#
#     # 没有前面的组，或本组 min_c 更小，才可能保留。
#     # best 为 None 时，or 短路，不会把数值与 None 比较。
#     if best is None or min_c < best:
#         # 同组已按 c 升序，前 cnt 条都是最小值，重复项全部保留。
#         for i in range(left, left + cnt):
#             index = nums[i][2]
#             seen.add(index)
#         best = min_c
#     left = right
#
# res = []
# for i in range(len(candidate)):
#     if i in seen:
#         res.append(candidate[i])
# print(res)
#
#
# # 思路
# # 1. 给每条轨迹带上原下标，然后排序，让相同 s 的轨迹相邻。
# #    排序只改 nums，不改 candidate。原下标不会因为排序而改变。
# # 2. 同一个 s 内，c 较大的轨迹一定被 c 最小的轨迹排除。
# #    所以一组只需要考虑最小 c；最小 c 的所有重复项都保留，不互相排除。
# # 3. 前面处理过的组都具有更小的 s，best 是这些原始轨迹中的最小 c。
# #    若 min_c >= best，就存在一条 s 更小、c 也不大的轨迹，本组不能保留。
# #    因此 min_c < best（或还没有 best）时，保留本组全部 cnt 条最小值。
# # 4. 同组按 c 升序，最小值正好占据 [left, left+cnt) 这段位置。
# #    逐项取出原下标 index=nums[i][2]，全部加入 seen，不能只记一个 index。
# #    当前例子中 nums[0]=(1,1,2)：left=0，而 index=2，指向 candidate[2]。
# #    保存 seen.add(2)，不是 seen.add(0)，否则会错误保留 candidate[0]=(1,2)。
# # 5. 更新 best 后，后面更大 s、且 c 不小于 best 的轨迹会被排除。
# #    排除要求另一条轨迹两项都不更差、且至少一项更好；完全相同不算更好。
# # 6. 最后按 i=0,1,... 遍历 candidate，i 在 seen 中才加入 res，恢复原顺序。
# #
# # 常见问题
# # 1. 时间复杂度是多少？
# #    统一先执行 nums.sort()，再线性扫描。最坏时间 O(n log n)，空间 O(n)。
# #    后续分组扫描是 O(n)，不能将整个算法说成总是 O(n)。
# #
# # 2. 为什么有两层 while，扫描仍然是 O(n)？
# #    right 每次处理一组，left 随后直接跳到 right；每条轨迹只扫描一次。
# #
# # 3. 为什么要把相同 s 的轨迹放在一组？
# #    同组里较小的 c 可以排除较大的 c，不能看见一条就立即决定保留。
# #    统计 cnt 是为了保留全部最小值重复项，不是用重复次数来排除它们。
# #
# # 4. 空间复杂度是多少？
# #    nums、seen 和 res 最多各存 O(n) 个元素，总额外空间 O(n)。
# #    包含输入存储后仍为 O(n)，不需要 deepcopy。
# #
# # 5. 为什么不用 -1 标记删除？
# #    会改动输入，也可能和合法数据冲突；记录保留下标更直接。
# #    这里仅将原轨迹引用加入 res，没有修改轨迹内部的值。
#
#
# # 以下为历史旧版本，逐行注释归档，不参与执行。
# # 注意：旧版将完全相同轨迹互相排除，与当前题意不符；以以上代码为准。
# # candidata = [(1, 1), (2, 2), (3, 3)]
# #
# # res = []
# # for i in range(len(candidata)):
# #     s1, c1 = candidata[i]
# #     flag = True
# #
# #     for j in range(len(candidata)):
# #         if i == j:
# #             continue
# #
# #         s2, c2 = candidata[j]
# #         # 按截图条件：两个指标都不小于另一条轨迹，就排除当前轨迹。
# #         if s1 >= s2 and c1 >= c2:
# #             flag = False
# #             break
# #
# #     if flag:
# #         res.append(candidata[i])
# # print(res)
# #
# #
# # # 思路
# # # 逐条判断轨迹 i 是否应该保留，再遍历其他轨迹 j。
# # # 只要存在 j，使 si >= sj 且 ci >= cj，就排除 i。
# # # 如果检查完所有其他轨迹仍未被排除，就加入 res，保留原输入顺序。
# # # 给定数据中，(2,2)、(3,3) 都满足相对 (1,1) 的排除条件。
# # # 输出：[(1, 1)]。
# # #
# # # 常见问题
# # # 1. 时间和空间复杂度是多少？
# # #    最坏每条轨迹都要和其他轨迹比较，时间 O(n²)。
# # #    不计输入和结果，辅助空间 O(1)；结果最多 O(n)，包含输入后也是 O(n)。
# # #
# # # 2. 为什么必须跳过 i == j？
# # #    每条轨迹和自身比较都满足两个 >=，不跳过就会把所有轨迹排除。
# # #
# # # 3. 为什么找到一条满足条件的轨迹就可以 break？
# # #    排除条件只要求存在一个这样的 j，找到之后 i 已经确定不保留。
# # #
# # # 4. 如果一条轨迹 s 小，但 c 大，应该排除哪条？
# # #    这两条轨迹不能仅凭彼此排除；需要继续检查其他轨迹。
# # #    最终结果可能不止一条，本题求的是剩余集合，并未给出唯一最优的打分规则。
# # #
# # # 5. 完全相同的两条轨迹怎么办？
# # #    确实要排除：条件是两个 >=（非严格），两条完全相同的轨迹
# # #    互相满足 si >= sj 且 ci >= cj，因此都被剔除，一条也不保留。
# # #    优化版对应"组内最小 c 必须唯一（cnt == 1）"这一步。
# # #
# # # 6. 为什么不边遍历边删除原列表？
# # #    删除会改变下标，也可能改变后续轨迹的比较对象。
# # #    对原列表逐条判断，再用新列表收集结果，逻辑更清楚。
# #
# # # n 条轨迹，
# # # (s, c) {(s1, c1), ...， (sn, cn)} cost 越小越好
# # # 选一条最好的轨迹
# # # 1. 排除掉一些 (si >= sj, ci >= cj) i 肯定比 j 更差， 把 i 排除；
# # # 求所有满足上述条件排除之后剩下的轨迹集合
# #
# # from copy import deepcopy
# # candidate=([1,2], [2,1],[1,1], [3,3])
# # tmp=[]
# # tmp = deepcopy(candidate)
# #
# # # for a in candidate:
# # #     b=a[0]
# # #     c=a[1]
# # #     d=[]
# # #     d.append(b)
# # #     d.append(c)
# # #     tmp.append(d)
# #
# # res=[]
# #
# # for j in  range(len(candidate)):
# #     
# #     for  i in range(len(candidate)):
# #         if i!=j and tmp[i][0]>=tmp[j][0] and tmp[i][1]>=tmp[j][1] :
# #             candidate[i][0]=-1
# #             candidate[i][1]=-1
# #         
# # for i in  range(len(candidate)):
# #     if candidate[i][0]!=-1:
# #         res.append(candidate[i])
# # print(res)
# # print(tmp)
# #
#
