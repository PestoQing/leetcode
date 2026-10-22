# 任务：选择满足限制的速度序列
# 某程序生成了多组候选速度序列。请检查它们是否满足给定限制，再从可行候选中选出与目标速度最接近的一组。
# 输入与假设
# - t：长度为 N 的公共时间列表，单位秒；N ≥ 2，所有时间有限且严格递增，可以不等间隔。
# - candidates：按输入顺序排列的 M 个候选，候选下标从 0 开始。每个候选是长度应为 N 的速度列表 v，速度单位 m/s。
# - v0：要求的初始速度；vmax：速度上界，单位均为 m/s。
# - amax：加速度绝对值上界，单位 m/s²；vref：目标速度，单位 m/s。
# - 全局参数必须是有限数，满足 vmax ≥ 0、amax ≥ 0、0 ≤ v0 ≤ vmax、0 ≤ vref ≤ vmax。全局参数或时间列表不合法时，返回 INVALID_INPUT，不再选择候选。
# - 候选长度错误，或含 NaN、正负无穷时，该候选不可行，继续检查其他候选。输入容器及元素数值类型正确，不要求处理字符串、空对象等类型错误。NaN、无穷除外，数值幅度合理，不考溢出处理。
# - 相邻时间点间的速度按直线插值，因而每一段加速度恒定。只检查整个 [t, t[N-1]] 范围内的速度与每段加速度；不约束节点处的加速度连续性，也不考位置、障碍物和车辆几何。无需建立坐标系或补充碰撞条件。
# 可行性、代价与输出
# 候选必须同时满足：
# 1. 初始速度 v = v0。
# 2. 所有速度点满足 0 ≤ v ≤ vmax；每段加速度绝对值不超过 amax，加速度由你根据时间和速度求出。
# 满足限制后计算节点速度均方误差：
# J = (1/N) × Σ(i=0…N-1) (v - vref)²。
# 这是按节点等权计算的指标，不是按时间积分；单位为 (m/s)²。选择 J 最小的可行候选；代价完全相等时选原始下标最小的候选。限制取等时算可行。按上述数学定义作答，不要求额外设计浮点容差。
# - 找到可行候选：返回 ("OK", 原始下标, J)。
# - 空候选列表或所有候选不可行：返回 ("NO_FEASIBLE", None, None)。
# - 全局输入不合法：返回 ("INVALID_INPUT", None, None)。
# 本题数据
# 1. 写出每段加速度的计算式，给出上述候选的可行性、淘汰原因及最终输出  2. 实现通用选择函数，包含输入检查、筛选、代价比较、平局和无可行候选处理，并说明时间与额外空间复杂度
t     = [0, 1, 3, 4]  
v0    = 2            
vmax  = 6            
amax  = 2            
vref  = 4            

candidates = [
  [2, 3,   4, 4],    # 下标 0，简称 A
  [2, 4.5, 4, 4],    # 下标 1，简称 B
  [2, 4,   4, 5],    # 下标 2，简称 C
  [2, 3,   5, 4],    # 下标 3，简称 D
  [2, 3,   7, 4],    # 下标 4，简称 E
]
n = len(t)
print(len(candidates))
best=1000000000000000000
for j in range(len(candidates)):
    nums = candidates[j]
    if nums[0] != v0:
        continue
    flag=True
    for x in nums:
        if x> vmax:
            flag =False
            break

    if not flag:
        continue

    for i in range(1,n):
        a=(nums[i]-nums[i-1])/(t[i]-t[i-1])
        if abs(a)>amax:
            flag=False
            break
    if not flag:
        continue

    res=0
    for x in nums:
        res+=(x-4)**2
    res /=n
    
    if res<best:
        best=res
        index=j
print(index)
if index is None:
    print("NO_FEASIBLE", None, None)
else:
    print("INVALID_INPUT", None, None)






