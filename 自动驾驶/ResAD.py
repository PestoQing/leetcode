# 题目描述：
# ResAD（Normalized Residual Trajectory Modeling, arXiv:2510.08562）的玩具复现。
# 自车在 (0,0)，速度 V0（带一点横向漂移），同车道前方有一辆慢车。
# 规划 4 秒 8 个航点：不直接预测轨迹，而是先用匀速模型外推"惯性参考"，
# 再预测"为什么必须偏离惯性"的残差，最后选出最优候选。
#
# 思路（与论文第 3.2、3.3 节对应）：
# 1. 惯性参考（式 3）：p_ti = p0 + v0·t_i，表示不做任何控制时车会去哪。
# 2. 残差（式 4）：r = τgt − τref，即驾驶员施加的修正量。
# 3. PRNorm（式 5、6）：对 x、y 两个分量分别在"整个训练集、所有航点"上
#    取 min / max，把残差线性缩放到 [−γ, γ]。这里用合成的专家轨迹充当训练集。
#    残差让目标分布集中在 0 附近；PRNorm 让 x、y 两个分量尺度一致，
#    避免数值大的分量（这里是纵向）主导损失。
# 4. 惯性参考扰动（式 7、8）：对初速度加 δv ~ N(0, diag(σvx², σvy²))，
#    得到 K 条不同的惯性参考，每条对应一个意图假设。
# 5. 去噪（式 9、10）：论文用学到的扩散解码器，这里换成"理想去噪器"：
#    以该参考下两种驾驶意图（跟车 / 左变道超车）的归一化残差为高斯混合先验，
#    闭式求后验均值；从纯高斯噪声出发做 2 步 DDIM。【简化】
# 6. 排序器：论文用 Transformer 打分并蒸馏 PDM 各子指标，这里直接用
#    规则版的 PDMS 近似（无碰撞 × 可行驶区域 × 进度/车道/舒适度加权）。【简化】
#
# 复杂度：训练集 M 条、K 个候选、N 个航点，统计 O(M·N)，去噪 O(K·N)。

import math

SEED = 7
N, DT = 8, 0.5                  # 8 个航点，间隔 0.5 s，共 4 s（与 NAVSIM 一致）
V0 = (8.0, 0.4)                 # 自车初速度 (vx, vy)，vy 表示航向略有偏差
LEAD_X0, LEAD_V = 20.0, 4.0     # 前车初始纵向位置与速度（同车道 y = 0）
LANE_W = 3.5                    # 车道宽，左侧车道中心 y = 3.5
M_DATA = 40                     # 合成训练集大小，仅用来统计 PRNorm 的 min / max
GAMMA, EPS0 = 1.0, 1e-6         # PRNorm 输出区间 [−γ, γ] 与防除零常数
K = 6                           # 扰动出的惯性参考 / 候选轨迹条数
SIGMA_VX, SIGMA_VY = 1.0, 0.3   # 速度扰动的纵向、横向标准差
MODE_STD = 0.08                 # 理想去噪器中每种意图的先验标准差（归一化空间）
ALPHAS = [0.05, 0.5, 1.0]       # ᾱ：从近似纯噪声 → 中间 → 干净，共 2 步 DDIM
TS = [DT * (i + 1) for i in range(N)]


def imul(a, b):
    return (a * b) & 0xffffffff


def mulberry32(seed):
    # 与 JS 版逐位一致的 32 位随机数，保证 py 和 html 的结果相同
    s = seed & 0xffffffff

    def rnd():
        nonlocal s
        s = (s + 0x6D2B79F5) & 0xffffffff
        t = imul(s ^ (s >> 15), s | 1)
        t = ((t + imul(t ^ (t >> 7), t | 61)) & 0xffffffff) ^ t
        return ((t ^ (t >> 14)) & 0xffffffff) / 4294967296
    return rnd


rnd = mulberry32(SEED)


def gauss():
    # Box-Muller，每次只取一个标准正态
    u1 = max(rnd(), 1e-12)
    u2 = rnd()
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def inertial_ref(v):
    # 式 (3)：没有任何控制输入时，车沿当前速度匀速前进
    return [(v[0] * t, v[1] * t) for t in TS]


def expert(v, mode, p):
    # 合成的"专家"轨迹。mode 0：跟车，匀减速到速度 p 并回到本车道中心；
    # mode 1：左变道超车，纵向加速度 p，3 秒内平滑移到左车道中心。
    pts = []
    for t in TS:
        if mode == 0:
            a = (v[0] - p) / TS[-1]
            pts.append((v[0] * t - 0.5 * a * t * t, 0.0))
        else:
            u = min(t / 3.0, 1.0)
            pts.append((v[0] * t + 0.5 * p * t * t, LANE_W * u * u * (3 - 2 * u)))
    return pts


def residual(gt, ref):
    # 式 (4)：逐点相减，残差就是"必须偏离惯性多少"
    return [(g[0] - r[0], g[1] - r[1]) for g, r in zip(gt, ref)]


# ---------- 1. 合成训练集，统计 PRNorm 所需的 min / max（式 5） ----------
data = []
for _ in range(M_DATA):
    v = (V0[0] + 1.5 * gauss(), 0.3 * gauss())
    mode = 0 if rnd() < 0.5 else 1
    p = 3.0 + 2.0 * rnd() if mode == 0 else 0.2 + 0.4 * rnd()
    gt = expert(v, mode, p)
    data.append((gt, residual(gt, inertial_ref(v))))

# 按分量 d ∈ {x, y} 在所有轨迹、所有航点上取极值（论文的做法，不是逐时刻统计）
rmin = [min(r[t][d] for _, r in data for t in range(N)) for d in range(2)]
rmax = [max(r[t][d] for _, r in data for t in range(N)) for d in range(2)]


def minmax(pts, lo, hi):
    # 式 (6)：r̃ = 2γ(r − rmin)/(rmax − rmin + ε0) − γ
    return [tuple(2 * GAMMA * (q[d] - lo[d]) / (hi[d] - lo[d] + EPS0) - GAMMA for d in range(2)) for q in pts]


def prdenorm(z):
    # PRNorm 的逆变换，把去噪得到的归一化残差还原成米
    return [tuple((q[d] + GAMMA) * (rmax[d] - rmin[d] + EPS0) / (2 * GAMMA) + rmin[d] for d in range(2)) for q in z]


def rms_per_t(seqs):
    # 每个航点目标值的均方根（米）：直接回归绝对坐标时，越远的点数值越大
    return [math.sqrt(sum(q[t][0] ** 2 + q[t][1] ** 2 for q in seqs) / len(seqs)) for t in range(N)]


def std_per_dim(seqs):
    # x、y 分量各自的标准差：不归一化时，纵向 x 的误差会压过横向 y
    out = []
    for d in range(2):
        vals = [q[t][d] for q in seqs for t in range(N)]
        mu = sum(vals) / len(vals)
        out.append(math.sqrt(sum((x - mu) ** 2 for x in vals) / len(vals)))
    return out


# 残差建模把分布拉到 0 附近；PRNorm 再把 x、y 缩放到同一区间，平衡两个分量的损失
rms_abs = rms_per_t([g for g, _ in data])
rms_res = rms_per_t([r for _, r in data])
std_res = std_per_dim([r for _, r in data])
std_norm = std_per_dim([minmax(r, rmin, rmax) for _, r in data])

# ---------- 2. 惯性参考扰动（式 7、8） ----------
vs = [(V0[0] + SIGMA_VX * gauss(), V0[1] + SIGMA_VY * gauss()) for _ in range(K)]
refs = [inertial_ref(v) for v in vs]


def flat(pts):
    return [c for q in pts for c in q]


def denoise(z, ab, modes):
    # 理想去噪器：先验为各意图归一化残差 m_j 处的各向同性高斯（等权重），
    # z = √ᾱ·x0 + √(1−ᾱ)·ε 时，后验均值有闭式解。
    var = ab * MODE_STD ** 2 + 1 - ab
    logw = [-sum((zi - math.sqrt(ab) * mi) ** 2 for zi, mi in zip(z, m)) / (2 * var) for m in modes]
    top = max(logw)
    w = [math.exp(x - top) for x in logw]
    w = [x / sum(w) for x in w]
    gain = math.sqrt(ab) * MODE_STD ** 2 / var
    x0 = [sum(w[j] * (modes[j][i] + gain * (z[i] - math.sqrt(ab) * modes[j][i])) for j in range(len(modes)))
          for i in range(len(z))]
    return x0, w


# ---------- 3. 从纯噪声出发，2 步 DDIM 去噪（式 9、10） ----------
cands = []
for k in range(K):
    # 条件 c：该扰动参考下的两种意图（论文中由参考的位置编码送入解码器）
    modes = [flat(minmax(residual(expert(vs[k], j, LEAD_V if j == 0 else 0.4), refs[k]), rmin, rmax))
             for j in range(2)]
    z = [gauss() for _ in range(2 * N)]
    for i in range(len(ALPHAS) - 1):
        a, a2 = ALPHAS[i], ALPHAS[i + 1]
        x0, w = denoise(z, a, modes)
        eps = [(zi - math.sqrt(a) * xi) / math.sqrt(1 - a) for zi, xi in zip(z, x0)]
        # DDIM 确定性更新：用预测的 x0 和 ε 跳到下一个噪声水平
        z = [math.sqrt(a2) * xi + math.sqrt(1 - a2) * ei for xi, ei in zip(x0, eps)]
    r = prdenorm([(z[2 * t], z[2 * t + 1]) for t in range(N)])
    # 预测残差加回对应的扰动参考，得到候选轨迹
    cands.append(([(f[0] + q[0], f[1] + q[1]) for f, q in zip(refs[k], r)], w))


# ---------- 4. 排序器：规则版 PDMS 近似 ----------
def score(traj, best_x):
    nc = 1.0
    for t, (x, y) in zip(TS, traj):
        if abs(y) < 2.0 and abs(x - (LEAD_X0 + LEAD_V * t)) < 6.0:
            nc = 0.0                       # 与前车包围盒重叠 → 碰撞
    dac = 1.0 if all(-1.75 <= y <= LANE_W + 1.75 for _, y in traj) else 0.0
    ep = traj[-1][0] / best_x              # 相对进度
    lk = max(0.0, 1 - min(abs(traj[-1][1]), abs(traj[-1][1] - LANE_W)) / 1.0)
    pts = [(0.0, 0.0)] + traj
    acc = max(math.hypot(pts[i + 1][0] - 2 * pts[i][0] + pts[i - 1][0], pts[i + 1][1] - 2 * pts[i][1] + pts[i - 1][1])
              for i in range(1, N)) / DT ** 2
    c = 1.0 if acc <= 4.0 else 0.0         # 舒适度：最大加速度不超过 4 m/s²
    return nc * dac * (5 * ep + 2 * lk + 2 * c) / 9


best_x = max(tr[-1][0] for tr, _ in cands)
scores = [score(tr, best_x) for tr, _ in cands]
best = max(range(K), key=lambda k: scores[k])

print("PRNorm rmin =", [f"{x:.4f}" for x in rmin], " rmax =", [f"{x:.4f}" for x in rmax])
print("RMS |τgt| per t =", " ".join(f"{x:.4f}" for x in rms_abs))
print("RMS |r|   per t =", " ".join(f"{x:.4f}" for x in rms_res))
print(f"std(x, y) residual = ({std_res[0]:.4f}, {std_res[1]:.4f})  after PRNorm = ({std_norm[0]:.4f}, {std_norm[1]:.4f})")
for k in range(K):
    tr, w = cands[k]
    print(f"cand {k}: v0'=({vs[k][0]:.4f}, {vs[k][1]:.4f})  w=[{w[0]:.4f}, {w[1]:.4f}]  "
          f"end=({tr[-1][0]:.4f}, {tr[-1][1]:.4f})  score={scores[k]:.4f}")
print(f"best = {best}  score = {scores[best]:.4f}")
