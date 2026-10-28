candidate = ([1, 2], [2, 1], [1, 1], [3, 3])

# 记录原下标，最后按输入顺序输出，不修改原始轨迹。
nums = []
for i in range(len(candidate)):
    nums.append((candidate[i][0], candidate[i][1], i))

# s 已经升序时不用排序，此时整体时间为 O(n)。
flag = True
for i in range(1, len(nums)):
    if nums[i][0] < nums[i - 1][0]:
        flag = False
        break
if not flag:
    nums.sort()

seen = set()
best = None
left = 0
while left < len(nums):
    # 同一个 s 的轨迹一起处理，找出最小 c 及其出现次数。
    right = left
    min_c = nums[left][1]
    cnt = 0
    index = nums[left][2]
    while right < len(nums) and nums[right][0] == nums[left][0]:
        if nums[right][1] < min_c:
            min_c = nums[right][1]
            cnt = 1
            index = nums[right][2]
        elif nums[right][1] == min_c:
            cnt += 1
        right += 1

    # 组内最小 c 必须唯一，并且不能被之前更小 s 的轨迹排除。
    # 完全相同的轨迹确实要排除：条件是 >=（非严格），
    # 两条相同轨迹互相满足 si >= sj 且 ci >= cj，都被剔除。
    if cnt == 1 and (best is None or min_c < best):
        seen.add(index)
    if best is None or min_c < best:
        best = min_c
    left = right

res = []
for i in range(len(candidate)):
    if i in seen:
        res.append(candidate[i])
print(res)


# 思路
# 按 s 升序处理，best 记录所有更小 s 的轨迹中的最小 c。
# 对相同 s 的一组轨迹，只有最小 c 才可能保留。
# 如果最小 c 重复出现，按截图两个 >= 的规则，它们会互相排除。
# 如果 best <= 本组最小 c，本组也全部被之前的轨迹排除。
# 即使一组没有保留任何轨迹，也要更新 best，因为排除条件针对原始集合。
# 最后按原下标收集结果，不改原数据，不用 -1 作删除标记。
#
# 常见问题
# 1. 整体真的是 O(n) 吗？
#    输入按 s 非递减排列时，是 O(n)；相同 s 内的 c 不必有序。
#    任意未排序输入需要先排序，最坏 O(n log n)，不能只算后续扫描的 O(n)。
#    当前给定输入未按 s 排序，会执行排序分支。题目没有给出值域限制，
#    不能直接假设可以用计数排序得到线性复杂度。
#
# 2. 为什么有两层 while，扫描仍然是 O(n)？
#    right 每次处理一组，left 随后直接跳到 right；每条轨迹只扫描一次。
#
# 3. 为什么要把相同 s 的轨迹放在一组？
#    同组里较小的 c 可以排除较大的 c，不能看见一条就立即决定保留。
#    还需要统计最小 c 的重复次数，保持原来的两个 >= 比较规则。
#
# 4. 空间复杂度是多少？
#    nums、seen 和 res 最多各存 O(n) 个元素，总额外空间 O(n)。
#    包含输入存储后仍为 O(n)，不需要 deepcopy。
#
# 5. 为什么不用 -1 标记删除？
#    会改动输入，也可能和合法数据冲突；记录保留下标更直接。
#    这里仅将原轨迹引用加入 res，没有修改轨迹内部的值。


# 以下为原文件完整内容，逐行注释保留，不参与执行。
# candidata = [(1, 1), (2, 2), (3, 3)]
#
# res = []
# for i in range(len(candidata)):
#     s1, c1 = candidata[i]
#     flag = True
#
#     for j in range(len(candidata)):
#         if i == j:
#             continue
#
#         s2, c2 = candidata[j]
#         # 按截图条件：两个指标都不小于另一条轨迹，就排除当前轨迹。
#         if s1 >= s2 and c1 >= c2:
#             flag = False
#             break
#
#     if flag:
#         res.append(candidata[i])
# print(res)
#
#
# # 思路
# # 逐条判断轨迹 i 是否应该保留，再遍历其他轨迹 j。
# # 只要存在 j，使 si >= sj 且 ci >= cj，就排除 i。
# # 如果检查完所有其他轨迹仍未被排除，就加入 res，保留原输入顺序。
# # 给定数据中，(2,2)、(3,3) 都满足相对 (1,1) 的排除条件。
# # 输出：[(1, 1)]。
# #
# # 常见问题
# # 1. 时间和空间复杂度是多少？
# #    最坏每条轨迹都要和其他轨迹比较，时间 O(n²)。
# #    不计输入和结果，辅助空间 O(1)；结果最多 O(n)，包含输入后也是 O(n)。
# #
# # 2. 为什么必须跳过 i == j？
# #    每条轨迹和自身比较都满足两个 >=，不跳过就会把所有轨迹排除。
# #
# # 3. 为什么找到一条满足条件的轨迹就可以 break？
# #    排除条件只要求存在一个这样的 j，找到之后 i 已经确定不保留。
# #
# # 4. 如果一条轨迹 s 小，但 c 大，应该排除哪条？
# #    这两条轨迹不能仅凭彼此排除；需要继续检查其他轨迹。
# #    最终结果可能不止一条，本题求的是剩余集合，并未给出唯一最优的打分规则。
# #
# # 5. 完全相同的两条轨迹怎么办？
# #    确实要排除：条件是两个 >=（非严格），两条完全相同的轨迹
# #    互相满足 si >= sj 且 ci >= cj，因此都被剔除，一条也不保留。
# #    优化版对应"组内最小 c 必须唯一（cnt == 1）"这一步。
# #
# # 6. 为什么不边遍历边删除原列表？
# #    删除会改变下标，也可能改变后续轨迹的比较对象。
# #    对原列表逐条判断，再用新列表收集结果，逻辑更清楚。
#
# # n 条轨迹，
# # (s, c) {(s1, c1), ...， (sn, cn)} cost 越小越好
# # 选一条最好的轨迹
# # 1. 排除掉一些 (si >= sj, ci >= cj) i 肯定比 j 更差， 把 i 排除；
# # 求所有满足上述条件排除之后剩下的轨迹集合
#
# from copy import deepcopy
# candidate=([1,2], [2,1],[1,1], [3,3])
# tmp=[]
# tmp = deepcopy(candidate)
#
# # for a in candidate:
# #     b=a[0]
# #     c=a[1]
# #     d=[]
# #     d.append(b)
# #     d.append(c)
# #     tmp.append(d)
#
# res=[]
#
# for j in  range(len(candidate)):
#     
#     for  i in range(len(candidate)):
#         if i!=j and tmp[i][0]>=tmp[j][0] and tmp[i][1]>=tmp[j][1] :
#             candidate[i][0]=-1
#             candidate[i][1]=-1
#         
# for i in  range(len(candidate)):
#     if candidate[i][0]!=-1:
#         res.append(candidate[i])
# print(res)
# print(tmp)
#
