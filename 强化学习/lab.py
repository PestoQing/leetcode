"""强化学习实验入口：在线算法阅读 cleanrl，离线算法对照 CORL。"""
import argparse, json, hashlib, random
import psutil

# 系统可用内存检查；硬CPU/内存限制由run.sh的systemd scope设置。
def guard():
    if psutil.virtual_memory().available < 8*1024**3:
        raise RuntimeError("可用内存不足8GiB，停止，不自动恢复")
from pathlib import Path
import numpy as np
import torch
from torch import nn
import gymnasium as gym
from stable_baselines3 import PPO, SAC

# IL/RL共用的MLP骨架：输入维度n→128→128→输出维度m。Actor为3→1，Q为4→1。
def net(n,m):
    return nn.Sequential(nn.Linear(n,128),nn.ReLU(),nn.Linear(128,128),nn.ReLU(),nn.Linear(128,m))

def main():
    # train更新模型；collect只采数据；evaluate冻结参数；plot只读日志。
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['train','collect','evaluate','plot'])
    p.add_argument('--algo',choices=['ppo','sac','bc','iql'],default='sac')
    p.add_argument('--steps',type=int,default=5000)
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--video',action='store_true'); p.add_argument('--model'); p.add_argument('--data',default='dataset.npz')
    p.add_argument('--out',default='runs/demo'); p.add_argument('--episodes',type=int,default=20)
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    # 固定初始化随机种子，并限制PyTorch内部线程，避免CPU过载。
    guard(); torch.set_num_threads(1); torch.manual_seed(a.seed); np.random.seed(a.seed); random.seed(a.seed)
    # 观测=[cosθ,sinθ,角速度]，动作是[-2,2]力矩。渲染只在--video时开启。
    env=gym.make('Pendulum-v1',render_mode='rgb_array' if a.video else None);
    if a.video: env=gym.wrappers.RecordVideo(env,str(out/'videos'),episode_trigger=lambda ep: ep==0)
    env.action_space.seed(a.seed)
    policy=net(3,1)
    # PPO/SAC的zip由SB3加载；BC/IQL的pt保存本地Actor权重。
    if a.model:
        if a.algo in ['ppo','sac']:
            model={'ppo':PPO,'sac':SAC}[a.algo].load(a.model,device='cpu')
        else: policy.load_state_dict(torch.load(a.model,weights_only=True))
    # 无--model时是随机策略，不是已经训练过的RL策略。
    def act(s):
        if not a.model: return env.action_space.sample()
        if a.algo in ['ppo','sac']: return model.predict(s,deterministic=True)[0]
        with torch.no_grad(): return (2*torch.tanh(policy(torch.tensor(s,dtype=torch.float32)))).numpy()
    if a.command=='train':
        # 在线训练会改变数据分布；IL常见的固定示范集与此不同。
        if a.algo in ['ppo','sac']:
            # 统一运行入口用成熟实现；原始算法逐行学习见 cleanrl 单文件。
            model={'ppo':PPO,'sac':SAC}[a.algo]('MlpPolicy',env,seed=a.seed,device='cpu',verbose=1,tensorboard_log=str(out))
            from stable_baselines3.common.callbacks import BaseCallback
            class ResourceGuard(BaseCallback):
                def _on_step(self):
                    if self.num_timesteps % 100 == 0:
                        try: guard()
                        except RuntimeError:
                            self.model.save(str(out/"resource-stop")); raise
                    return True
            # PPO的总步数按完整rollout取整，5000可能实际采6144步。
            model.learn(a.steps,callback=ResourceGuard()); model.save(str(out/'model'))
        else:
            import copy
            # 离线数据：s[B,3]、a[B,1]、r[B,1]、s′[B,3]、terminated[B,1]。
            d=np.load(a.data); s,ac,r,ns,t=[torch.tensor(d[k],dtype=torch.float32) for k in ['observation','action','reward','next_observation','terminated']]
            # 统一列向量，防止广播把[B]与[B,1]意外变成[B,B]。
            r=r.reshape(-1,1); t=t.reshape(-1,1)
            # Q(s,a)输入状态+动作；V(s)只输入状态；tq是缓慢跟随的目标网络。
            q1=net(4,1); q2=net(4,1); v=net(3,1); tq1=copy.deepcopy(q1); tq2=copy.deepcopy(q2)
            # Actor、双Q、V分开维护Adam；各自的梯度不会混用。
            po=torch.optim.Adam(policy.parameters(),lr=3e-4)
            qo=torch.optim.Adam(list(q1.parameters())+list(q2.parameters()),lr=3e-4); vo=torch.optim.Adam(v.parameters(),lr=3e-4)
            log=[]
            for step in range(a.steps):
                if step%100==0: guard()
                # 在固定数据上有放回采样；离线训练不调用env.step补新经验。
                idx=torch.randint(len(s),(256,)); x,u,y,z,done=s[idx],ac[idx],r[idx],ns[idx],t[idx]
                # 普通BC每条示范权重为1；IQL根据优势重新加权。
                weight=torch.ones((256,1))
                if a.algo=='iql':
                    # 偏向较高价值的 expectile 拟合数据内动作的价值。
                    # target不反传：取数据动作的双Q较小值，减少过高估计。
                    with torch.no_grad(): target=torch.minimum(tq1(torch.cat([x,u],1)),tq2(torch.cat([x,u],1)))
                    # Expectile：δ>0权重0.7，δ≤0权重0.3，拟合数据内较好动作的价值。
                    diff=target-v(x); vl=(torch.where(diff>0,.7,.3)*diff.square()).mean()
                    # 清梯度→反传→更新V；这对应IL中熟悉的一个监督训练step。
                    vo.zero_grad(); vl.backward(); vo.step()
                    # Bellman目标用更新后的V；时间截断仍bootstrap，真正终止才乘0。
                    # β=3放大正优势；上限100避免指数权重极端增大。
                    with torch.no_grad(): bellman=y+.99*(1-done)*v(z); weight=torch.exp(3*(target-v(x))).clamp(max=100)
                    # 拼接[s,a]得到[B,4]，双Q都拟合同一个Bellman监督目标。
                    xu=torch.cat([x,u],1); ql=((q1(xu)-bellman).square()+(q2(xu)-bellman).square()).mean()
                    # Q更新后再软更新目标Q：target←0.995target+0.005Q。
                    qo.zero_grad(); ql.backward(); qo.step()
                    with torch.no_grad():
                        for source,target_net in [(q1,tq1),(q2,tq2)]:
                            for src,dst in zip(source.parameters(),target_net.parameters()): dst.lerp_(src,.005)
                # 确定性优势加权 BC；对应 CORL deterministic actor 变体。
                # IL类比：BC拟合动作；IQL同样拟合动作，但好动作的误差权重更大。
                # Actor输出tanh×2映射到力矩范围；weights已经detach，不反传到Q/V。
                loss=(weight*(2*torch.tanh(policy(x))-u).square()).mean()
                # loss.backward计算所有Actor参数梯度；Adam实际使用一/二阶矩更新。
                po.zero_grad(); loss.backward(); po.step()
                if step%100==0: log.append({'update':step,'actor_loss':loss.item()})
            torch.save(policy.state_dict(),out/'model.pt'); (out/'loss.json').write_text(json.dumps(log))
        (out/'config.json').write_text(json.dumps(vars(a),indent=2))
    elif a.command=='collect':
        # 转移采集保存真实后继状态，再处理reset；不能把下一局初态当作s′。
        data={k:[] for k in ['observation','action','reward','next_observation','terminated','truncated','episode']}
        s,_=env.reset(seed=a.seed); ep=0
        for _ in range(a.steps):
            u=act(s); ns,r,t,tr,_=env.step(u)
            for k,val in zip(data,[s,u,r,ns,t,tr,ep]): data[k].append(val)
            s=ns
            # terminated=任务结束；truncated=时间限制；两者都需要reset但bootstrap语义不同。
            if t or tr: ep+=1; s,_=env.reset()
        np.savez_compressed(a.data,**{k:np.array(v) for k,v in data.items()})
        Path(a.data+'.json').write_text(json.dumps({'source':vars(a),'sha256':hashlib.sha256(Path(a.data).read_bytes()).hexdigest()},indent=2))
    elif a.command=='evaluate':
        # 与训练独立：固定20个种子，每回合200步；不更新模型，不向经验池回写。
        scores=[]
        for seed in range(10000,10000+a.episodes):
            s,_=env.reset(seed=seed); total=0
            for _ in range(200):
                s,r,t,tr,_=env.step(act(s)); total+=r
                if t or tr: break
            scores.append(total)
        # mean越大越好；std是回合间波动，不是多训练种子的置信区间。
        result={'returns':scores,'mean':float(np.mean(scores)),'std':float(np.std(scores))}; print(result)
        (out/'evaluation.json').write_text(json.dumps(result,indent=2))
    else:
        # actor_loss是训练拟合误差，不是环境回报；低loss不保证闭环效果好。
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        log=json.loads((out/'loss.json').read_text()); plt.plot([x['update'] for x in log],[x['actor_loss'] for x in log]); plt.xlabel('updates'); plt.ylabel('actor loss'); plt.savefig(out/'loss.png')
    env.close()
if __name__=='__main__': main()
