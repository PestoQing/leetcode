"""逐轮强化学习教学引擎：所有动作、奖励与梯度均由真实 Gymnasium/PyTorch 计算。

与 IL 对照：BC 的监督目标是数据动作；PPO 的监督信号是优势；
SAC 用 Q 为可微策略提供方向；IQL 则把优势变成 BC 的样本权重。
这是小网络、单批更新的教学配置，不是复现论文性能的 benchmark。
一轮 = 每个相关优化器各更新一次，然后在同一初态跑完整的 200 步评估。
评估数据绝不加入训练集，因而不会破坏 IQL/BC 的离线训练设定。
"""
import copy
import hashlib
import json
import math
import time
from pathlib import Path

import gymnasium as gym
import numpy as np
import psutil
import torch
from torch import nn
from torch.distributions import Normal

ROOT = Path(__file__).resolve().parent


def check_memory():
    """周期性守卫；CPU/RAM 硬上限由托管整个服务的 systemd cgroup 执行。"""
    if psutil.virtual_memory().available < 8 * 1024 ** 3:
        raise RuntimeError('可用内存低于 8GiB，已暂停；不自动重试。')


def mlp(n, m):
    """观测 [B,3] → 隐层 [B,32] → 输出。小网络让单轮更新足够快。"""
    return nn.Sequential(nn.Linear(n, 32), nn.Tanh(), nn.Linear(32, 32), nn.Tanh(), nn.Linear(32, m))


class Actor(nn.Module):
    """与 IL 相同的观测编码骨架；RL 另外需要动作分布来计算 log π。"""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(nn.Linear(3, 32), nn.Tanh(), nn.Linear(32, 32), nn.Tanh())
        self.mean = nn.Linear(32, 1)
        self.log_std = nn.Parameter(torch.tensor([-0.5]))

    def distribution(self, obs):
        # 高斯分布是未压缩动作 z 的分布，标准差始终为正。
        mean = self.mean(self.features(obs))
        return Normal(mean, self.log_std.clamp(-5, 1).exp().expand_as(mean))

    def deterministic(self, obs):
        # IL/评估用确定性均值；tanh 后乘 2 对齐 Pendulum 力矩 [-2,2]。
        return 2 * torch.tanh(self.distribution(obs).mean)

    def sample(self, obs):
        # SAC 用 rsample 重参数化，使 Q(s,a) 的梯度能经动作反传给 Actor。
        dist = self.distribution(obs)
        z = dist.rsample()
        y = torch.tanh(z)
        action = 2 * y
        # 变量变换的雅可比包含 tanh 和乘2，不能将 z 的密度当作动作密度。
        log_prob = (dist.log_prob(z) - torch.log(2 * (1 - y.square()) + 1e-6)).sum(-1, keepdim=True)
        return action, log_prob


def optimizer_step(loss, optimizer, parameter, name, max_norm=None):
    """执行真实 Adam，并记录一个标量参数的完整计算链。

    网络含上千参数，界面只手推输出偏置第一个元素；其余参数同样参与更新。
    不能直接写 θ←θ−lr*g 冒充 Adam：它还包含一阶/二阶矩和偏置修正。
    """
    optimizer.zero_grad(set_to_none=True)
    before = parameter.detach().flatten()[0].item()
    loss.backward()
    raw_grad = parameter.grad.detach().flatten()[0].item()
    norm = None
    if max_norm is not None:
        # PPO 全网络梯度裁剪；展示裁剪前和真正交给 Adam 的梯度。
        params = [p for group in optimizer.param_groups for p in group['params']]
        norm = float(nn.utils.clip_grad_norm_(params, max_norm))
    grad = parameter.grad.detach().flatten()[0].item()
    optimizer.step()
    state = optimizer.state[parameter]
    step = int(state['step'].item())
    m = state['exp_avg'].flatten()[0].item()
    v = state['exp_avg_sq'].flatten()[0].item()
    group = optimizer.param_groups[0]
    beta1, beta2 = group['betas']
    # PyTorch Adam 默认无 weight_decay；按实际优化器超参逐项计算。
    m_hat = m / (1 - beta1 ** step)
    v_hat = v / (1 - beta2 ** step)
    delta = -group['lr'] * m_hat / (math.sqrt(v_hat) + group['eps'])
    after = parameter.detach().flatten()[0].item()
    return dict(name=name, loss=float(loss.detach()), before=before, grad_raw=raw_grad,
                grad=grad, grad_norm=norm, clip_norm=max_norm, lr=group['lr'], beta1=beta1,
                beta2=beta2, eps=group['eps'], step=step, m=m, v=v, m_hat=m_hat,
                v_hat=v_hat, predicted_delta=delta, actual_delta=after-before, after=after,
                predicted_after=before+delta)


class Experiment:
    def __init__(self, algo, seed=0, lr=0.003):
        check_memory()
        torch.set_num_threads(1)
        torch.manual_seed(seed)
        self.rng = np.random.default_rng(seed)
        self.algo, self.seed, self.lr = algo, seed, lr
        self.round = 0
        self.ppo_cache = None
        self.ppo_epoch = 0
        self.gamma = 0.99
        self.env = gym.make('Pendulum-v1')
        self.env.action_space.seed(seed)
        self.obs, _ = self.env.reset(seed=seed)
        self.actor = Actor()
        self.value = mlp(3, 1)
        self.q1, self.q2 = mlp(4, 1), mlp(4, 1)
        self.tq1, self.tq2 = copy.deepcopy(self.q1), copy.deepcopy(self.q2)
        self.log_alpha = nn.Parameter(torch.tensor(math.log(.2)))
        # PPO 的 Actor/Critic 联合更新；其他算法分别维护各自 Adam 状态。
        self.ppo_opt = torch.optim.Adam(list(self.actor.parameters()) + list(self.value.parameters()), lr=lr)
        self.actor_opt = torch.optim.Adam(self.actor.parameters(), lr=lr)
        self.q_opt = torch.optim.Adam(list(self.q1.parameters()) + list(self.q2.parameters()), lr=lr)
        self.v_opt = torch.optim.Adam(self.value.parameters(), lr=lr)
        self.alpha_opt = torch.optim.Adam([self.log_alpha], lr=lr)
        self.buffer = []
        self.history = []
        self.name = f'{time.time_ns()}_{algo}_s{seed}'
        self.folder = ROOT / 'runs' / 'live' / self.name
        self.folder.mkdir(parents=True)
        # 冻结实际执行源码与关键依赖版本，避免未来修改后失去计算依据。
        (self.folder/'live_engine.py').write_bytes(Path(__file__).read_bytes())
        (self.folder/'dependencies.json').write_text(json.dumps(dict(torch=torch.__version__,gymnasium=gym.__version__,numpy=np.__version__),indent=2))
        # 离线算法只在初始化生成一次训练数据。之后训练绝不调用 env.step。
        if algo in ('bc', 'iql'):
            self.make_offline_data()
        if algo == 'sac':
            self.collect(512, random_actions=True)
        self.initial_hash = self.actor_hash()
        baseline = self.evaluate()
        self.history.append(dict(round=0, evaluation=baseline, trace=None, actor_hash=self.initial_hash))
        self.persist(self.history[0])

    def actor_hash(self):
        data = b''.join(p.detach().cpu().numpy().tobytes() for p in self.actor.parameters())
        return hashlib.sha256(data).hexdigest()

    def make_offline_data(self):
        """用脚本控制器+随机动作生成固定转移。它是启发式教师，并非专家保证。"""
        env = gym.make('Pendulum-v1')
        obs, _ = env.reset(seed=self.seed + 200)
        for _ in range(2048):
            theta = math.atan2(float(obs[1]), float(obs[0]))
            omega = float(obs[2])
            # 近直立时 PD 稳定；其他角度按能量差泵能量。并混入30%随机行为。
            energy = .5 * omega ** 2 + 15 * (math.cos(theta) - 1)
            u = -8 * theta - 2 * omega if abs(theta) < .45 and abs(omega) < 2 else -0.3 * energy * omega
            u = float(np.clip(u, -2, 2))
            if self.rng.random() < .3:
                u = float(self.rng.uniform(-2, 2))
            action = np.array([u], dtype=np.float32)
            nxt, reward, terminated, truncated, _ = env.step(action)
            self.buffer.append((obs.copy(), action.copy(), reward, nxt.copy(), terminated, truncated))
            obs = nxt
            if terminated or truncated:
                obs, _ = env.reset()
        env.close()
        np.savez_compressed(self.folder / 'frozen-data.npz',
                            observation=np.array([x[0] for x in self.buffer]),
                            action=np.array([x[1] for x in self.buffer]),
                            reward=np.array([x[2] for x in self.buffer]),
                            next_observation=np.array([x[3] for x in self.buffer]),
                            terminated=np.array([x[4] for x in self.buffer]),
                            truncated=np.array([x[5] for x in self.buffer]))
        self.data_hash = hashlib.sha256((self.folder/'frozen-data.npz').read_bytes()).hexdigest()

    def collect(self, count, random_actions=False):
        """SAC 在线经验池。评估另外用独立环境，绝不回流这里。"""
        for _ in range(count):
            with torch.no_grad():
                obs = torch.tensor(self.obs, dtype=torch.float32).unsqueeze(0)
                action = self.rng.uniform(-2, 2, (1,)).astype(np.float32) if random_actions else self.actor.sample(obs)[0][0].numpy()
            nxt, r, term, trunc, _ = self.env.step(action)
            self.buffer.append((self.obs.copy(), action.copy(), r, nxt.copy(), term, trunc))
            self.obs = nxt
            if term or trunc:
                self.obs, _ = self.env.reset()
        # 教学会话上限50轮，因此内存有界；离线数据不走这个分支。
        self.buffer = self.buffer[-8192:]

    def batch(self):
        idx = self.rng.integers(0, len(self.buffer), size=64)
        rows = [self.buffer[int(i)] for i in idx]
        s = torch.tensor(np.array([x[0] for x in rows]), dtype=torch.float32)
        a = torch.tensor(np.array([x[1] for x in rows]), dtype=torch.float32)
        r = torch.tensor([x[2] for x in rows], dtype=torch.float32).unsqueeze(1)
        ns = torch.tensor(np.array([x[3] for x in rows]), dtype=torch.float32)
        done = torch.tensor([x[4] for x in rows], dtype=torch.float32).unsqueeze(1)
        return s, a, r, ns, done

    def evaluate(self):
        """每次参数更新后调用一次：固定种子10000、固定200步，公平对比行为变化。

        不生成重负载光追视频。保存真实物理状态，由网页 canvas 逐帧画摆杆。
        每个 frame 的奖励是执行该 frame 动作得到的奖励，最后一帧没有后续动作。
        """
        env = gym.make('Pendulum-v1')
        obs, _ = env.reset(seed=10000)
        frames, total = [], 0.
        for _ in range(200):
            with torch.no_grad():
                u = float(self.actor.deterministic(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))[0, 0])
            nxt, reward, term, trunc, _ = env.step(np.array([u], dtype=np.float32))
            total += float(reward)
            frames.append(dict(theta=math.atan2(float(obs[1]), float(obs[0])), omega=float(obs[2]),
                               action=u, reward=float(reward), total=total))
            obs = nxt
            if term or trunc:
                break
        frames.append(dict(theta=math.atan2(float(obs[1]), float(obs[0])), omega=float(obs[2]), action=0., reward=0., total=total))
        env.close()
        return dict(seed=10000, return_=total, steps=len(frames)-1, frames=frames)

    def ppo_update(self):
        """与 IL 的区别：动作是旧策略自己采样的，标签是 GAE 优势而非专家动作。

        用未压缩高斯 z 计算 log概率；执行动作2*tanh(z)。同一z的新旧动作变换
        雅可比会抵消，因此概率比可以在z空间精确计算。单轮只做一次联合梯度更新，连续4轮复用同一rollout。
        """
        # 同一个rollout复用4次，每次只做一个step并立即仿真。
        # 因而第1步ratio=1，后续步ratio随策略改变，clipping真正参与更新。
        if self.ppo_cache is None or self.ppo_epoch == 4:
            rows = []
            for _ in range(256):
                s = torch.tensor(self.obs, dtype=torch.float32).unsqueeze(0)
                with torch.no_grad():
                    dist = self.actor.distribution(s)
                    z = dist.sample()
                    action = (2 * torch.tanh(z))[0].numpy()
                    old_log = dist.log_prob(z).sum(-1).item()
                    value = self.value(s).item()
                nxt, r, term, trunc, _ = self.env.step(action)
                with torch.no_grad():
                    next_value = 0. if term else self.value(torch.tensor(nxt,dtype=torch.float32).unsqueeze(0)).item()
                rows.append(dict(s=self.obs.copy(), z=z[0].numpy(), reward=r, value=value,
                                 next_value=next_value, logp=old_log, term=term, trunc=trunc))
                self.obs = nxt
                if term or trunc:
                    self.obs, _ = self.env.reset()
            # delta=r+gamma*V(s')-V(s)。截断可bootstrap，但GAE不能跨新episode串接。
            advantages = []
            gae = 0.
            for row in reversed(rows):
                delta = row['reward'] + self.gamma * row['next_value'] - row['value']
                gae = delta + self.gamma * .95 * (not(row['term'] or row['trunc'])) * gae
                advantages.append(gae)
            advantages.reverse()
            self.ppo_cache = (rows, advantages)
            self.ppo_epoch = 0
        rows, advantages = self.ppo_cache
        self.ppo_epoch += 1
        raw_adv = torch.tensor(advantages, dtype=torch.float32)
        values = torch.tensor([x['value'] for x in rows], dtype=torch.float32)
        targets = raw_adv + values
        adv = (raw_adv - raw_adv.mean()) / (raw_adv.std(unbiased=False) + 1e-8)
        s = torch.tensor(np.array([x['s'] for x in rows]), dtype=torch.float32)
        z = torch.tensor(np.array([x['z'] for x in rows]), dtype=torch.float32)
        old_log = torch.tensor([x['logp'] for x in rows], dtype=torch.float32)
        # 所有256样本构成一批。同rollout第1次更新前ratio=1，之后由新旧策略差异决定。
        dist = self.actor.distribution(s)
        logp = dist.log_prob(z).sum(-1)
        ratio = torch.exp(logp-old_log)
        clipped = ratio.clamp(.8,1.2)
        surrogate = torch.minimum(ratio*adv,clipped*adv)
        policy_loss = -surrogate.mean()
        value_loss = (self.value(s).flatten()-targets).square().mean()
        entropy = dist.entropy().sum(-1).mean()
        loss = policy_loss + .5*value_loss - .01*entropy
        # 对Actor输出偏置b手推梯度：∂logN(z;μ,σ)/∂b=(z−μ)/σ²。
        # 正优势超过上界/负优势低于下界时，clipped目标变平，该样本梯度为0。
        # 未压缩高斯熵对均值偏置的导数为0。
        d_logp = ((z-dist.mean)/dist.variance).sum(-1).detach()
        active = ~(((adv>0)&(ratio.detach()>1.2))|((adv<0)&(ratio.detach()<.8)))
        actor_grad_samples = -adv * ratio.detach() * d_logp * active
        gradient_check = dict(formula='g_b=mean(−A×ρ×(z−μ)/σ²×未进入裁剪平坦区的掩码)',
                              sample_mu=float(dist.mean[0,0].detach()), sample_sigma=float(dist.stddev[0,0].detach()),
                              sample_dlogp=float(d_logp[0]), sample_gradient_active=bool(active[0]),sample_gradient=float(actor_grad_samples[0]),
                              analytic_batch_gradient=float(actor_grad_samples.mean()))
        sample = rows[0]
        sample_trace = dict(state=sample['s'].tolist(), latent_z=sample['z'].tolist(), action=(2*np.tanh(sample['z'])).tolist(), reward=sample['reward'], value=sample['value'], next_value=sample['next_value'],
                            delta=sample['reward']+.99*sample['next_value']-sample['value'],
                            gae=raw_adv[0].item(), target=targets[0].item(), advantage=adv[0].item(),
                            old_logp=old_log[0].item(), new_logp=logp[0].item(), ratio=ratio[0].item(),
                            clipped=clipped[0].item(), surrogate=surrogate[0].item())
        losses = dict(policy=policy_loss.item(), value=value_loss.item(), entropy=entropy.item(), total=loss.item(),clip_fraction=float(((ratio.detach()<.8)|(ratio.detach()>1.2)).float().mean()),rollout_epoch=self.ppo_epoch)
        update = optimizer_step(loss,self.ppo_opt,self.actor.mean.bias,'Actor.mean.bias[0]（与Critic联合）',.5)
        return dict(algorithm='PPO', source=f'旧策略在线采样256步；本rollout第{self.ppo_epoch}/4次更新', batch=256,
                    formulas=['δ=r+0.99V(s′)−V(s)', 'GAE=δ+0.99×0.95×下一个GAE（episode边界截断）',
                              'A标准化=(GAE−均值)/标准差；target=GAE+旧V',
                              'ρ=exp(logπ新−logπ旧)；Lπ=−mean(min(ρA,clip(ρ)A))',
                              'L=Lπ+0.5Lvalue−0.01H'],sample=sample_trace,losses=losses,updates=[update],gradient_check=gradient_check,
                    note='小网络PPO：同一rollout做4次全批更新，每次更新后独立仿真。第1步ratio=1，后续步可触发裁剪；用满4步后重新采样。熵项在未压缩高斯空间计算。')

    def offline_update(self):
        s,a,r,ns,done = self.batch()
        # 固定数据用于BC监督或IQL价值学习。评估轨迹不在self.buffer中。
        updates, losses = [], {}
        weights = torch.ones_like(r)
        sample = dict(state=s[0].tolist(), next_state=ns[0].tolist(), action=float(a[0,0]),reward=float(r[0,0]),terminated=bool(done[0,0]))
        if self.algo == 'iql':
            with torch.no_grad():
                q_data = torch.minimum(self.tq1(torch.cat([s,a],1)),self.tq2(torch.cat([s,a],1)))
            value = self.value(s)
            diff = q_data-value
            asym = torch.where(diff>0,.7,.3)
            vl = (asym*diff.square()).mean()
            sample.update(q=float(q_data[0,0]),v_before=float(value[0,0].detach()),diff=float(diff[0,0].detach()),
                          expectile_weight=float(asym[0,0]),expectile_sample_loss=float((asym*diff.square())[0,0].detach()))
            updates.append(optimizer_step(vl,self.v_opt,self.value[-1].bias,'V.output.bias[0]'))
            with torch.no_grad():
                target = r+.99*(1-done)*self.value(ns)
                advantage = q_data-self.value(s)
                weights = torch.exp(3*advantage).clamp(max=100)
            xu=torch.cat([s,a],1)
            ql=((self.q1(xu)-target).square()+(self.q2(xu)-target).square()).mean()
            updates.append(optimizer_step(ql,self.q_opt,self.q1[-1].bias,'Q1.output.bias[0]（Q1/Q2联合）'))
            with torch.no_grad():
                for src,dst in [(self.q1,self.tq1),(self.q2,self.tq2)]:
                    for p,tp in zip(src.parameters(),dst.parameters()):tp.lerp_(p,.005)
            sample.update(q_target=float(target[0,0]),advantage=float(advantage[0,0]),weight=float(weights[0,0]))
            losses.update(value=vl.item(),q=ql.item())
        prediction=self.actor.deterministic(s)
        mse=(prediction-a).square()
        actor_loss=(weights*mse).mean()
        # 与IL的链式法则完全相同，仅IQL多一个已detach的样本权重w。
        # π=2tanh(μ)，所以∂π/∂b=2(1−(π/2)²)。
        d_action = 2 * (1-(prediction.detach()/2).square())
        grad_samples = 2 * weights * (prediction.detach()-a) * d_action
        gradient_check = dict(formula='g_b=mean(2w(π−a)×2(1−(π/2)²))；BC中w=1',
                              sample_error=float((prediction.detach()-a)[0,0]),
                              sample_daction=float(d_action[0,0]),sample_weight=float(weights[0,0]),
                              sample_gradient=float(grad_samples[0,0]),analytic_batch_gradient=float(grad_samples.mean()))
        sample.update(prediction=float(prediction[0,0].detach()),mse=float(mse[0,0].detach()),
                      weight=float(weights[0,0]),weighted_error=float((weights*mse)[0,0].detach()))
        updates.append(optimizer_step(actor_loss,self.actor_opt,self.actor.mean.bias,'Actor.mean.bias[0]'))
        losses['actor']=actor_loss.item()
        return dict(algorithm=self.algo.upper(),source='初始化冻结的2048条脚本教师+随机转移',batch=64,
                    data_hash=self.data_hash,sample=sample,losses=losses,updates=updates,gradient_check=gradient_check,
                    formulas=['BC: L=mean((2tanh(μ(s))−a数据)²)' ] if self.algo=='bc' else
                             ['V: δ=min(Qtarget1,Qtarget2)−V；L=mean(|0.7−1[δ<0]|δ²)',
                              'Q: y=r+0.99(1−terminated)V新(s′)；L=mean((Q1−y)²+(Q2−y)²)',
                              'target Q ← 0.995 target Q+0.005 Q新',
                              'Actor: w=min(exp(3(Qtarget数据−V新)),100)；L=mean(w(π(s)−a数据)²)'],
                    note='每轮V、Q、Actor各更新一次。BC只更新Actor。训练不再与环境交互；每轮之后的独立仿真只做评估。')

    def sac_update(self):
        self.collect(64)
        s,a,r,ns,done=self.batch()
        alpha=self.log_alpha.exp().detach()
        with torch.no_grad():
            na,nlogp=self.actor.sample(ns)
            soft_q=torch.minimum(self.tq1(torch.cat([ns,na],1)),self.tq2(torch.cat([ns,na],1)))-alpha*nlogp
            target=r+.99*(1-done)*soft_q
        qa=torch.cat([s,a],1)
        ql=((self.q1(qa)-target).square()+(self.q2(qa)-target).square()).mean()
        updates=[optimizer_step(ql,self.q_opt,self.q1[-1].bias,'Q1.output.bias[0]（Q1/Q2联合）')]
        # Actor更新期间冻结Q参数，但保留Q对动作的导数，使Actor仍能利用Q学习。
        for p in list(self.q1.parameters())+list(self.q2.parameters()):p.requires_grad_(False)
        action,logp=self.actor.sample(s)
        q_pi=torch.minimum(self.q1(torch.cat([s,action],1)),self.q2(torch.cat([s,action],1)))
        actor_loss=(alpha*logp-q_pi).mean()
        # Q对动作的导数由真实Q网络autograd得到，再手推Actor输出偏置的链式梯度。
        dq_da = torch.autograd.grad(q_pi.sum(),action,retain_graph=True)[0].detach()
        y=action.detach()/2
        d_action=2*(1-y.square())
        d_logp=4*y*(1-y.square())/(2*(1-y.square())+1e-6)
        grad_samples=alpha*d_logp-dq_da*d_action
        gradient_check=dict(formula='g_b=mean(α·∂logπ/∂μ − (∂Q/∂a)·2(1−tanh²z))',
                            sample_dlogp=float(d_logp[0,0]),sample_dqda=float(dq_da[0,0]),
                            sample_daction=float(d_action[0,0]),sample_gradient=float(grad_samples[0,0]),
                            analytic_batch_gradient=float(grad_samples.mean()))
        sample=dict(state=s[0].tolist(), next_state=ns[0].tolist(), action=float(a[0,0]), reward=float(r[0,0]),terminated=bool(done[0,0]),alpha=float(alpha),
                    next_logp=float(nlogp[0,0]),soft_next_q=float(soft_q[0,0]),q_target=float(target[0,0]),
                    logp=float(logp[0,0].detach()),q_pi=float(q_pi[0,0].detach()),
                    actor_sample_loss=float((alpha*logp-q_pi)[0,0].detach()))
        updates.append(optimizer_step(actor_loss,self.actor_opt,self.actor.mean.bias,'Actor.mean.bias[0]'))
        for p in list(self.q1.parameters())+list(self.q2.parameters()):p.requires_grad_(True)
        # 目标熵为−动作维度=−1。logp.detach：温度更新不再改变Actor。
        alpha_loss=-(self.log_alpha*(logp.detach()-1)).mean()
        updates.append(optimizer_step(alpha_loss,self.alpha_opt,self.log_alpha,'log_alpha[0]'))
        with torch.no_grad():
            for src,dst in [(self.q1,self.tq1),(self.q2,self.tq2)]:
                for p,tp in zip(src.parameters(),dst.parameters()):tp.lerp_(p,.005)
        return dict(algorithm='SAC',source=f'在线经验池{len(self.buffer)}条；本轮新增64步',batch=64,
                    sample=sample,losses=dict(q=ql.item(),actor=actor_loss.item(),temperature=alpha_loss.item()),updates=updates,gradient_check=gradient_check,
                    formulas=['y=r+0.99(1−terminated)(min Qtarget(s′,a′)−αlogπ(a′|s′))',
                              'Q: mean((Q1−y)²+(Q2−y)²)', 'Actor: mean(αlogπ(a|s)−min Q新(s,a))',
                              '温度: −mean(logα×detach(logπ−1))；α=exp(logα)',
                              'target Q ← 0.995 target Q+0.005 Q新'],
                    note='同一轮Q、Actor、温度各做一次Adam更新，接着仿真。logπ是连续概率密度的对数，可以为正。')

    def update(self):
        check_memory()
        if self.round>=50:raise RuntimeError('本次会话已达到50轮，请创建新实验继续学习。')
        before=self.actor_hash()
        old_parameters={name:p.detach().clone() for name,p in self.actor.named_parameters()}
        if self.algo=='ppo':trace=self.ppo_update()
        elif self.algo=='sac':trace=self.sac_update()
        else:trace=self.offline_update()
        actor_update=next(x for x in trace['updates'] if x['name'].startswith('Actor.'))
        trace['gradient_check']['autograd_batch_gradient']=actor_update['grad_raw']
        trace['gradient_check']['difference']=trace['gradient_check']['analytic_batch_gradient']-actor_update['grad_raw']
        self.round+=1
        # 核心承诺：每一次完整算法更新后，立刻运行一次真实环境评估。
        evaluation=self.evaluate()
        changes=[]
        for name,p in self.actor.named_parameters():
            prev=old_parameters[name]
            changes.append(dict(name=name,shape=list(p.shape),before=prev.flatten().tolist(),
                                after=p.detach().flatten().tolist(),
                                grad=None if p.grad is None else p.grad.detach().flatten().tolist(),
                                delta_norm=float((p.detach()-prev).norm())))
        record=dict(round=self.round,evaluation=evaluation,trace=trace,actor_hash=self.actor_hash(),previous_actor_hash=before,
                    parameters=changes)
        self.persist(record)
        self.history.append(record)
        return record

    def persist(self,record):
        """每轮独立落盘：数值、实际轨迹、全部网络与优化器、训练环境和随机数状态。"""
        # 这些文件用于审计/复现。UI不在出错后自动加载并继续训练。
        (self.folder/f'round-{record["round"]:03}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False))
        payload=dict(actor=self.actor.state_dict(),value=self.value.state_dict(),q1=self.q1.state_dict(),q2=self.q2.state_dict(),
                     tq1=self.tq1.state_dict(),tq2=self.tq2.state_dict(),log_alpha=self.log_alpha.detach(),
                     ppo_opt=self.ppo_opt.state_dict(),actor_opt=self.actor_opt.state_dict(),q_opt=self.q_opt.state_dict(),
                     v_opt=self.v_opt.state_dict(),alpha_opt=self.alpha_opt.state_dict(),round=self.round,
                     algo=self.algo,seed=self.seed,lr=self.lr,torch_rng=torch.get_rng_state(),np_rng=self.rng.bit_generator.state,
                     env_state=self.env.unwrapped.state.copy(),elapsed_steps=self.env._elapsed_steps,
                     env_rng=self.env.unwrapped.np_random.bit_generator.state,buffer=self.buffer,
                     ppo_cache=self.ppo_cache,ppo_epoch=self.ppo_epoch)
        torch.save(payload,self.folder/f'round-{record["round"]:03}.pt')
        (self.folder/'config.json').write_text(json.dumps(dict(algorithm=self.algo,seed=self.seed,lr=self.lr,
              gamma=.99,evaluation_seed=10000,evaluation_steps=200,round_definition='每个相关优化器各更新一次，然后仿真一次',
              source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),data_hash=self.data_hash if hasattr(self,'data_hash') else None),ensure_ascii=False,indent=2))

    def close(self):
        self.env.close()
