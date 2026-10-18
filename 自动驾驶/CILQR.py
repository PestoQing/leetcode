# 题目描述：
# 自车沿直车道行驶，车道中心 y = 0，目标速度 V_REF。前方有一辆障碍车（可静止或匀速），
# 用椭圆安全域表示。要求规划未来 N 步的控制量 (a, δ)，使轨迹尽量贴近车道中心、
# 保持目标速度、控制平滑，同时满足：
#   1. 加速度 a ∈ [A_MIN, A_MAX]，前轮转角 δ ∈ [-D_MAX, D_MAX]；
#   2. 每个时刻自车位置都在障碍物椭圆之外。
# 这是 CILQR（Constrained Iterative LQR，Chen 等 2017）的最小实现。
#
# 思路：
# 1. 车辆模型：运动学自行车模型，状态 s = (x, y, v, θ)，控制 u = (a, δ)。
#    x' = x + v cosθ·dt，y' = y + v sinθ·dt，v' = v + a·dt，θ' = θ + v tanδ / L·dt。
# 2. iLQR：在当前轨迹附近把动力学线性化（A = ∂f/∂s，B = ∂f/∂u），把代价二阶展开，
#    backward pass 从末端往回求每步的前馈 k 和反馈增益 K；
#    forward pass 用 u_new = u + α·k + K·(s_new − s) 真实前推，线搜索步长 α。
# 3. 约束：iLQR 本身不能处理不等式约束 c(s, u) ≤ 0。CILQR 用指数障碍函数
#    b = q1·exp(q2·c) 把约束变成代价：c 越接近 0（越接近违反）代价增长越快。
#    其导数 ∇b = q1 q2 e^{q2 c} ∇c；Hessian 只保留半正定的一项
#    ∇²b ≈ q1 q2² e^{q2 c} ∇c ∇cᵀ，保证 Quu 正定、backward pass 稳定。
# 4. Levenberg-Marquardt 正则：Quu 加 λI。forward 成功则 λ 减半（更像牛顿法、走得快），
#    失败则 λ ×10（更像梯度下降、更保守）。
# 5. 初始控制全 0：直行会穿过障碍物，障碍代价很大；迭代后轨迹被推到障碍物一侧。
#
# 复杂度：每次迭代 O(N·n³)，n = 4 为状态维数，共迭代 MAX_ITER 次以内。

import math

# ---------------- 参数 ----------------
DT, N, WHEELBASE = 0.1, 30, 2.7
X0 = [0.0, 0.0, 8.0, 0.0]            # 初始状态 (x, y, v, θ)
V_REF = 8.0                          # 目标速度
W_Y, W_V, W_TH = 1.0, 0.5, 2.0       # 状态跟踪权重：横向偏差、速度偏差、航向
R_A, R_D = 0.2, 4.0                  # 控制权重：加速度、前轮转角
A_MIN, A_MAX, D_MAX = -4.0, 2.0, 0.35
OBS = [16.0, 0.4, 0.0, 0.0]          # 障碍车 (x, y, vx, vy)：初始位置与速度
OBS_A, OBS_B = 5.0, 2.2              # 椭圆安全域半轴：纵向、横向（已含车身与安全距离）
Q1_U, Q2_U = 1.0, 8.0                # 控制约束的障碍函数参数
Q1_O, Q2_O = 2.0, 6.0                # 避障约束的障碍函数参数
MAX_ITER, TOL = 30, 1e-4
ALPHAS = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125]


# ---------------- 小矩阵工具（不依赖 numpy） ----------------
def mat_mul(P, Q):
    return [[sum(P[i][k] * Q[k][j] for k in range(len(Q))) for j in range(len(Q[0]))] for i in range(len(P))]


def mat_vec(P, v):
    return [sum(P[i][k] * v[k] for k in range(len(v))) for i in range(len(P))]


def tr(P):
    return [list(r) for r in zip(*P)]


def add(P, Q):
    return [[P[i][j] + Q[i][j] for j in range(len(P[0]))] for i in range(len(P))]


def inv2(M):
    # 2×2 闭式求逆；调用前已保证正定，det > 0
    det = M[0][0] * M[1][1] - M[0][1] * M[1][0]
    return [[M[1][1] / det, -M[0][1] / det], [-M[1][0] / det, M[0][0] / det]]


# ---------------- 动力学与线性化 ----------------
def step(s, u):
    x, y, v, th = s
    a, d = u
    return [x + v * math.cos(th) * DT, y + v * math.sin(th) * DT, v + a * DT, th + v * math.tan(d) / WHEELBASE * DT]


def jac(s, u):
    # A = ∂f/∂s，B = ∂f/∂u，在当前 (s, u) 处一阶展开
    _, _, v, th = s
    _, d = u
    A = [[1, 0, math.cos(th) * DT, -v * math.sin(th) * DT],
         [0, 1, math.sin(th) * DT, v * math.cos(th) * DT],
         [0, 0, 1, 0],
         [0, 0, math.tan(d) / WHEELBASE * DT, 1]]
    B = [[0, 0], [0, 0], [DT, 0], [0, v / (WHEELBASE * math.cos(d) ** 2) * DT]]
    return A, B


def rollout(us):
    xs = [X0[:]]
    for u in us:
        xs.append(step(xs[-1], u))
    return xs


# ---------------- 约束：c ≤ 0 为满足 ----------------
def obs_c(s, k):
    # 椭圆外 c < 0，椭圆内 c > 0；障碍物按匀速外推到第 k 步
    ox, oy = OBS[0] + OBS[2] * k * DT, OBS[1] + OBS[3] * k * DT
    dx, dy = s[0] - ox, s[1] - oy
    c = 1 - (dx / OBS_A) ** 2 - (dy / OBS_B) ** 2
    grad = [-2 * dx / OBS_A ** 2, -2 * dy / OBS_B ** 2, 0, 0]
    return c, grad


def u_cons(u):
    # 四个约束：a ≤ A_MAX，A_MIN ≤ a，δ ≤ D_MAX，−D_MAX ≤ δ；返回 (c, ∇c)
    a, d = u
    return [(a - A_MAX, [1, 0]), (A_MIN - a, [-1, 0]), (d - D_MAX, [0, 1]), (-D_MAX - d, [0, -1])]


def barrier(c, q1, q2):
    # b = q1·e^{q2 c}，db/dc = q1 q2 e^{q2 c}，Hessian 系数 q1 q2² e^{q2 c}
    e = q1 * math.exp(q2 * c)
    return e, e * q2, e * q2 * q2


# ---------------- 代价及其导数 ----------------
def stage_cost(s, u, k):
    _, y, v, th = s
    J = W_Y * y * y + W_V * (v - V_REF) ** 2 + W_TH * th * th
    if u is not None:
        J += R_A * u[0] ** 2 + R_D * u[1] ** 2
        for c, _ in u_cons(u):
            J += barrier(c, Q1_U, Q2_U)[0]
    J += barrier(obs_c(s, k)[0], Q1_O, Q2_O)[0]
    return J


def total_cost(xs, us):
    return sum(stage_cost(xs[k], us[k], k) for k in range(N)) + stage_cost(xs[N], None, N)


def stage_derivs(s, u, k):
    # 返回 lx (4), lxx (4×4), lu (2), luu (2×2)；状态与控制的代价不耦合，lux = 0
    _, y, v, th = s
    lx = [0, 2 * W_Y * y, 2 * W_V * (v - V_REF), 2 * W_TH * th]
    lxx = [[0] * 4 for _ in range(4)]
    lxx[1][1], lxx[2][2], lxx[3][3] = 2 * W_Y, 2 * W_V, 2 * W_TH
    c, g = obs_c(s, k)
    _, b1, b2 = barrier(c, Q1_O, Q2_O)
    for i in range(4):
        lx[i] += b1 * g[i]
        for j in range(4):
            lxx[i][j] += b2 * g[i] * g[j]
    if u is None:
        return lx, lxx, None, None
    lu = [2 * R_A * u[0], 2 * R_D * u[1]]
    luu = [[2 * R_A, 0], [0, 2 * R_D]]
    for c, g in u_cons(u):
        _, b1, b2 = barrier(c, Q1_U, Q2_U)
        for i in range(2):
            lu[i] += b1 * g[i]
            for j in range(2):
                luu[i][j] += b2 * g[i] * g[j]
    return lx, lxx, lu, luu


# ---------------- backward pass ----------------
def backward(xs, us, lam):
    Vx, Vxx, _, _ = stage_derivs(xs[N], None, N)
    ks, Ks = [None] * N, [None] * N
    for k in range(N - 1, -1, -1):
        lx, lxx, lu, luu = stage_derivs(xs[k], us[k], k)
        A, B = jac(xs[k], us[k])
        At, Bt = tr(A), tr(B)
        Qx = [lx[i] + v for i, v in enumerate(mat_vec(At, Vx))]
        Qu = [lu[i] + v for i, v in enumerate(mat_vec(Bt, Vx))]
        Qxx = add(lxx, mat_mul(At, mat_mul(Vxx, A)))
        Quu = add(luu, mat_mul(Bt, mat_mul(Vxx, B)))
        Qux = mat_mul(Bt, mat_mul(Vxx, A))
        # LM 正则：Quu + λI，λ 越大步子越小越稳
        Quu[0][0] += lam
        Quu[1][1] += lam
        if Quu[0][0] <= 0 or Quu[0][0] * Quu[1][1] - Quu[0][1] * Quu[1][0] <= 0:
            return None, None  # 非正定：调用方增大 λ 重来
        Qi = inv2(Quu)
        kk = [-v for v in mat_vec(Qi, Qu)]
        KK = [[-v for v in row] for row in mat_mul(Qi, Qux)]
        # 值函数更新：V = Q 在最优 δu = k + K δx 处的二次型
        Kt = tr(KK)
        Vx = [Qx[i] + a + b + c for i, (a, b, c) in
              enumerate(zip(mat_vec(Kt, mat_vec(Quu, kk)), mat_vec(Kt, Qu), mat_vec(tr(Qux), kk)))]
        Vxx = add(add(Qxx, mat_mul(Kt, mat_mul(Quu, KK))), add(mat_mul(Kt, Qux), mat_mul(tr(Qux), KK)))
        Vxx = [[(Vxx[i][j] + Vxx[j][i]) / 2 for j in range(4)] for i in range(4)]
        ks[k], Ks[k] = kk, KK
    return ks, Ks


# ---------------- forward pass ----------------
def forward(xs, us, ks, Ks, alpha):
    nx, nu = [X0[:]], []
    for k in range(N):
        dx = [nx[k][i] - xs[k][i] for i in range(4)]
        fb = mat_vec(Ks[k], dx)
        u = [us[k][i] + alpha * ks[k][i] + fb[i] for i in range(2)]
        nu.append(u)
        nx.append(step(nx[k], u))
    return nx, nu


def main():
    us = [[0.0, 0.0] for _ in range(N)]
    xs = rollout(us)
    J = total_cost(xs, us)
    lam = 1.0
    print(f"iter 0  cost={J:.4f}  (初始：控制全 0，直行)")
    for it in range(1, MAX_ITER + 1):
        ks, Ks = backward(xs, us, lam)
        while ks is None:
            lam *= 10
            ks, Ks = backward(xs, us, lam)
        accepted = False
        for alpha in ALPHAS:
            nx, nu = forward(xs, us, ks, Ks, alpha)
            nJ = total_cost(nx, nu)
            if nJ < J:
                accepted = True
                break
        if accepted:
            rel = (J - nJ) / J
            xs, us, J = nx, nu, nJ
            lam = max(lam * 0.5, 1e-3)
            print(f"iter {it}  cost={J:.4f}  lambda={lam:.4f}  alpha={alpha:.4f}  接受")
            if rel < TOL:
                print("相对下降小于 TOL，收敛")
                break
        else:
            lam *= 10
            print(f"iter {it}  cost={J:.4f}  lambda={lam:.4f}  alpha=-  拒绝")
    # 检查约束：避障看 c 的最大值，控制看是否越界
    max_c = max(obs_c(xs[k], k)[0] for k in range(N + 1))
    u_ok = all(A_MIN <= a <= A_MAX and -D_MAX <= d <= D_MAX for a, d in us)
    for k in range(0, N + 1, 5):
        x, y, v, th = xs[k]
        print(f"k={k:2d}  x={x:.4f}  y={y:.4f}  v={v:.4f}  theta={th:.4f}")
    print(f"避障 max c={max_c:.4f}  {'满足' if max_c <= 0 else '违反'}；控制约束 {'满足' if u_ok else '违反'}")


if __name__ == "__main__":
    main()
