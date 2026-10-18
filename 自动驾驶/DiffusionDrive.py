# 题目描述：
# 三车道 BEV 场景：车道宽 LANE_W，车道中心 y = +LANE_W（左）、0（中）、-LANE_W（右）。
# 自车在中间车道原点、朝 +x、速度 V0；障碍车静止在 OBS_LANE 车道、纵向位置 OBS_X 处
# （OBS_LANE = None 表示没有障碍车）。规划未来 H 个航点（间隔 DT 秒）的轨迹。
# 用 DiffusionDrive（CVPR 2025）的"截断扩散 + 锚点"思想做一个玩具但忠实的实现：
#   1. 锚点词表：合成一批专家轨迹，k-means 聚成 K 条锚点轨迹；
#   2. 截断扩散：给每条锚点只加 T_TRUNC 步的小噪声，再用 DDIM 只去噪 2 步；
#   3. 打分：cost（碰撞 / 偏离车道 / 舒适度 / 效率）→ 置信度 softmax(−cost)，选最高者；
#   4. 对比：从纯高斯噪声出发同样走 2 步，观察"模式平均"。
#
# 思路：
# 1. 轨迹 = 2H 维向量 (x1, y1, ..., xH, yH)，除以 (SX, SY) 归一化后再做扩散。
# 2. 去噪网络用"理想去噪器"代替：当前场景下专家轨迹分布是高斯混合（左变道 / 右变道 /
#    巡航 / 减速跟停，权重由场景决定），E[x0 | xt] 有闭式解。训练充分的网络在
#    均方误差下学到的正是这个后验均值，所以它是网络的"满分替身"。
# 3. 截断的意义：锚点已在某个模式附近，只加少量噪声时后验几乎只落在最近的模式上，
#    2 步就能去噪到干净、多样的轨迹；纯噪声出发时后验在各模式间摊开，
#    2 步得到的是各模式的加权平均——两条车道之间、或直接撞向障碍车。
#
# 复杂度：k-means O(ITER·N·K·H)；每条轨迹每步去噪 O(M·H)，M 为混合成分数。

import math

# ---------------- 参数 ----------------
H, DT, T_LC = 8, 0.5, 3.0       # 航点数、航点间隔(s)、变道用时(s)
V0, LANE_W = 10.0, 3.5          # 自车速度(m/s)、车道宽(m)
OBS_LANE, OBS_X = 0, 22.0       # 障碍车所在车道（1 左 / 0 中 / -1 右 / None 无）与纵向位置
N_EXPERT, K, KM_ITERS = 48, 6, 5
SX, SY = 20.0, 2.0              # 归一化尺度：纵向 / 横向
SIG = 0.05                      # 混合成分的标准差（归一化后）
T, T_TRUNC = 1000, 50
SEED = 2025


# ---------------- 随机数：mulberry32 + Box-Muller（与网页 JS 版逐位一致） ----------------
state = SEED & 0xffffffff


def imul(a, b):
    # 模拟 JS 的 Math.imul：32 位整数乘法只保留低 32 位
    return (a * b) & 0xffffffff


def rand():
    global state
    state = (state + 0x6D2B79F5) & 0xffffffff
    t = imul(state ^ (state >> 15), state | 1)
    t = ((t + imul(t ^ (t >> 7), t | 61)) & 0xffffffff) ^ t
    return (t ^ (t >> 14)) / 4294967296


def gauss():
    # 1 - rand() 落在 (0, 1]，避免 log(0)
    u1, u2 = 1 - rand(), rand()
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


# ---------------- 轨迹生成与坐标归一化 ----------------
def rollout(v, a, dy):
    # 纵向匀加速（减到 0 就停住，不倒车）；横向用 smoothstep 在 T_LC 秒内平滑移动 dy
    pts = []
    for i in range(1, H + 1):
        t = i * DT
        x = -v * v / (2 * a) if a < 0 and v + a * t < 0 else v * t + 0.5 * a * t * t
        u = min(t / T_LC, 1.0)
        pts += [x, dy * (3 * u * u - 2 * u ** 3)]
    return pts


def norm(p):
    return [p[i] / (SX if i % 2 == 0 else SY) for i in range(2 * H)]


def denorm(p):
    return [p[i] * (SX if i % 2 == 0 else SY) for i in range(2 * H)]


def dist2(p, q):
    return sum((p[i] - q[i]) ** 2 for i in range(len(p)))


# ---------------- 1. 专家数据 → k-means 锚点词表 ----------------
# 四种行为轮流生成：0 巡航、1 左变道、2 右变道、3 减速，速度与幅度带随机扰动
experts = []
for n in range(N_EXPERT):
    m, v = n % 4, V0 + 1.5 * gauss()
    a = -2.5 + 0.5 * gauss() if m == 3 else 0.4 * gauss()
    dy = [0, LANE_W, -LANE_W, 0][m] + 0.2 * gauss()
    experts.append(norm(rollout(v, a, dy)))

# 取前 K 条为初始中心：行为轮流生成，前 K 条一定覆盖四种行为
centers = [list(e) for e in experts[:K]]
for it in range(KM_ITERS):
    # 分配：每条专家轨迹归到最近的中心
    assign = [min(range(K), key=lambda k: dist2(e, centers[k])) for e in experts]
    # 更新：中心 = 成员均值；空簇保留原中心
    for k in range(K):
        mem = [experts[n] for n in range(N_EXPERT) if assign[n] == k]
        if mem:
            centers[k] = [sum(e[i] for e in mem) / len(mem) for i in range(2 * H)]
anchors = centers

# ---------------- 2. 场景条件下的专家分布：高斯混合 ----------------
# 权重由场景决定：被障碍车占的车道不会变道进去；本车道有障碍时巡航权重为 0，改为跟停
# 权重不必归一化：后验责任里会被约掉
blocked = OBS_LANE == 0
gap = OBS_X - 8.0                                  # 跟停时离障碍车留 8 m（车长 + 安全距离）
modes = []                                         # (名称, 权重, 归一化均值)
for name, lane in [('左变道', 1), ('右变道', -1)]:
    if OBS_LANE != lane:
        modes.append((name, 0.35 if blocked else 0.15, norm(rollout(V0, 0.0, lane * LANE_W))))
if blocked:
    modes.append(('减速跟停', 0.3, norm(rollout(V0, -V0 * V0 / (2 * gap), 0.0))))
else:
    modes.append(('巡航', 0.6, norm(rollout(V0, 0.0, 0.0))))
    modes.append(('减速', 0.1, norm(rollout(V0, -1.5, 0.0))))

# ---------------- 3. DDPM 线性 β 调度 ----------------
# ab[t] = ᾱ_t = Π(1 − β_i)，ab[0] = 1 表示完全干净
ab = [1.0]
for i in range(1, T + 1):
    beta = 1e-4 + (0.02 - 1e-4) * (i - 1) / (T - 1)
    ab.append(ab[-1] * (1 - beta))


def denoise(xt, t):
    # 理想去噪器 E[x0 | xt]：xt = √ᾱ x0 + √(1−ᾱ) ε，x0 ~ Σ w_m N(μ_m, SIG² I)
    # 成分 m 下 xt 的边缘分布是 N(√ᾱ μ_m, s² I)，s² = ᾱ SIG² + 1 − ᾱ
    a = ab[t]
    s2 = a * SIG * SIG + 1 - a
    logw = [math.log(w) - dist2(xt, [math.sqrt(a) * u for u in mu]) / (2 * s2) for _, w, mu in modes]
    mx = max(logw)                                 # log-sum-exp，防止 exp 下溢
    r = [math.exp(l - mx) for l in logw]
    r = [x / sum(r) for x in r]
    # 成分内后验均值：μ_m + c (xt − √ᾱ μ_m)，c = √ᾱ SIG² / s²；再按责任 r 加权
    c = math.sqrt(a) * SIG * SIG / s2
    out = [0.0] * (2 * H)
    for (_, _, mu), rm in zip(modes, r):
        for i in range(2 * H):
            out[i] += rm * (mu[i] + c * (xt[i] - math.sqrt(a) * mu[i]))
    return out, r


def ddim(xt, ts):
    # DDIM（η = 0）：先预测 x0，再反推 ε，确定性地跳到下一个时间步
    for t, s in zip(ts, ts[1:]):
        x0, _ = denoise(xt, t)
        eps = [(xt[i] - math.sqrt(ab[t]) * x0[i]) / math.sqrt(1 - ab[t]) for i in range(2 * H)]
        xt = [math.sqrt(ab[s]) * x0[i] + math.sqrt(1 - ab[s]) * eps[i] for i in range(2 * H)]
    return xt


# ---------------- 4. 打分：cost 与置信度 ----------------
def cost(p):
    xs, ys = p[0::2], p[1::2]
    col = lane = comf = 0.0
    vx, vy = V0, 0.0
    px = py = 0.0
    for i in range(H):
        # 碰撞：航点落进障碍车椭圆安全域（纵 6 m、横 2.2 m）的深度
        if OBS_LANE is not None:
            col += max(0.0, 1 - ((xs[i] - OBS_X) / 6) ** 2 - ((ys[i] - OBS_LANE * LANE_W) / 2.2) ** 2)
        # 舒适度：由相邻航点差分出速度、再差分出加速度
        nvx, nvy = (xs[i] - px) / DT, (ys[i] - py) / DT
        comf += ((nvx - vx) / DT) ** 2 + ((nvy - vy) / DT) ** 2
        vx, vy, px, py = nvx, nvy, xs[i], ys[i]
    # 偏离车道：最后 3 个航点到最近车道中心的距离；骑线行驶最差
    for y in ys[-3:]:
        lane += min(abs(y - k * LANE_W) for k in (-1, 0, 1)) ** 2
    prog = max(0.0, 1 - xs[-1] / (V0 * H * DT))    # 效率：比匀速少走的比例
    return 20 * col + 0.5 * lane + 0.1 * comf / H + 3 * prog


def score(trajs):
    cs = [cost(p) for p in trajs]
    mx = max(-c for c in cs)
    e = [math.exp(-c - mx) for c in cs]
    return cs, [x / sum(e) for x in e]


# ---------------- 5. 截断扩散：锚点 + 小噪声 → DDIM 2 步 ----------------
# 前向加噪只到 T_TRUNC：x_T' = √ᾱ a_k + √(1−ᾱ) ε，锚点的形状基本保留
a50 = ab[T_TRUNC]
noisy = [[math.sqrt(a50) * v + math.sqrt(1 - a50) * gauss() for v in a] for a in anchors]
plans = [denorm(ddim(x, [T_TRUNC, T_TRUNC // 2, 0])) for x in noisy]
costs, conf = score(plans)
best = max(range(K), key=lambda k: conf[k])

# ---------------- 6. 对比：纯高斯噪声出发，同样只走 2 步 ----------------
pure = [denorm(ddim([gauss() for _ in range(2 * H)], [T, T // 2, 0])) for _ in range(K)]
pcosts = [cost(p) for p in pure]

print('锚点（k-means 中心）终点：')
for k in range(K):
    e = denorm(anchors[k])
    print(f'  a{k}: ({e[-2]:.4f}, {e[-1]:.4f})')
print(f'截断扩散 t: {T_TRUNC} -> {T_TRUNC // 2} -> 0，ᾱ_{T_TRUNC} = {a50:.4f}')
for k in range(K):
    p = plans[k]
    print(f'  模态 {k}: 终点 ({p[-2]:.4f}, {p[-1]:.4f})  cost {costs[k]:.4f}  置信度 {conf[k]:.4f}')
print(f'选中模态 {best}：cost {costs[best]:.4f}，置信度 {conf[best]:.4f}')
print(f'纯噪声 t: {T} -> {T // 2} -> 0，ᾱ_{T} = {ab[T]:.6f}')
for k in range(K):
    p = pure[k]
    print(f'  样本 {k}: 终点 ({p[-2]:.4f}, {p[-1]:.4f})  cost {pcosts[k]:.4f}')
print(f'纯噪声最优 cost {min(pcosts):.4f}  vs  截断扩散最优 cost {costs[best]:.4f}')
