"""强化学习实验入口：在线算法阅读 cleanrl，离线算法对照 CORL。"""
import argparse, json, hashlib, random
import psutil

def guard():
    if psutil.virtual_memory().available < 8*1024**3:
        raise RuntimeError("可用内存不足8GiB，停止，不自动恢复")
from pathlib import Path
import numpy as np
import torch
from torch import nn
import gymnasium as gym
from stable_baselines3 import PPO, SAC

def net(n,m):
    return nn.Sequential(nn.Linear(n,128),nn.ReLU(),nn.Linear(128,128),nn.ReLU(),nn.Linear(128,m))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['train','collect','evaluate','plot'])
    p.add_argument('--algo',choices=['ppo','sac','bc','iql'],default='sac')
    p.add_argument('--steps',type=int,default=5000)
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--video',action='store_true'); p.add_argument('--model'); p.add_argument('--data',default='dataset.npz')
    p.add_argument('--out',default='runs/demo'); p.add_argument('--episodes',type=int,default=20)
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    guard(); torch.set_num_threads(1); torch.manual_seed(a.seed); np.random.seed(a.seed); random.seed(a.seed)
    env=gym.make('Pendulum-v1',render_mode='rgb_array' if a.video else None);
    if a.video: env=gym.wrappers.RecordVideo(env,str(out/'videos'),episode_trigger=lambda ep: ep==0)
    env.action_space.seed(a.seed)
    policy=net(3,1)
    if a.model:
        if a.algo in ['ppo','sac']:
            model={'ppo':PPO,'sac':SAC}[a.algo].load(a.model,device='cpu')
        else: policy.load_state_dict(torch.load(a.model,weights_only=True))
    def act(s):
        if not a.model: return env.action_space.sample()
        if a.algo in ['ppo','sac']: return model.predict(s,deterministic=True)[0]
        with torch.no_grad(): return (2*torch.tanh(policy(torch.tensor(s,dtype=torch.float32)))).numpy()
    if a.command=='train':
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
            model.learn(a.steps,callback=ResourceGuard()); model.save(str(out/'model'))
        else:
            import copy
            d=np.load(a.data); s,ac,r,ns,t=[torch.tensor(d[k],dtype=torch.float32) for k in ['observation','action','reward','next_observation','terminated']]
            r=r.reshape(-1,1); t=t.reshape(-1,1)
            q1=net(4,1); q2=net(4,1); v=net(3,1); tq1=copy.deepcopy(q1); tq2=copy.deepcopy(q2)
            po=torch.optim.Adam(policy.parameters(),lr=3e-4)
            qo=torch.optim.Adam(list(q1.parameters())+list(q2.parameters()),lr=3e-4); vo=torch.optim.Adam(v.parameters(),lr=3e-4)
            log=[]
            for step in range(a.steps):
                if step%100==0: guard()
                idx=torch.randint(len(s),(256,)); x,u,y,z,done=s[idx],ac[idx],r[idx],ns[idx],t[idx]
                weight=torch.ones((256,1))
                if a.algo=='iql':
                    # 高分位 expectile 拟合数据内动作的价值。
                    with torch.no_grad(): target=torch.minimum(tq1(torch.cat([x,u],1)),tq2(torch.cat([x,u],1)))
                    diff=target-v(x); vl=(torch.where(diff>0,.7,.3)*diff.square()).mean()
                    vo.zero_grad(); vl.backward(); vo.step()
                    with torch.no_grad(): bellman=y+.99*(1-done)*v(z); weight=torch.exp(3*(target-v(x))).clamp(max=100)
                    xu=torch.cat([x,u],1); ql=((q1(xu)-bellman).square()+(q2(xu)-bellman).square()).mean()
                    qo.zero_grad(); ql.backward(); qo.step()
                    with torch.no_grad():
                        for source,target_net in [(q1,tq1),(q2,tq2)]:
                            for src,dst in zip(source.parameters(),target_net.parameters()): dst.lerp_(src,.005)
                # 确定性优势加权 BC；对应 CORL deterministic actor 变体。
                loss=(weight*(2*torch.tanh(policy(x))-u).square()).mean()
                po.zero_grad(); loss.backward(); po.step()
                if step%100==0: log.append({'update':step,'actor_loss':loss.item()})
            torch.save(policy.state_dict(),out/'model.pt'); (out/'loss.json').write_text(json.dumps(log))
        (out/'config.json').write_text(json.dumps(vars(a),indent=2))
    elif a.command=='collect':
        data={k:[] for k in ['observation','action','reward','next_observation','terminated','truncated','episode']}
        s,_=env.reset(seed=a.seed); ep=0
        for _ in range(a.steps):
            u=act(s); ns,r,t,tr,_=env.step(u)
            for k,val in zip(data,[s,u,r,ns,t,tr,ep]): data[k].append(val)
            s=ns
            if t or tr: ep+=1; s,_=env.reset()
        np.savez_compressed(a.data,**{k:np.array(v) for k,v in data.items()})
        Path(a.data+'.json').write_text(json.dumps({'source':vars(a),'sha256':hashlib.sha256(Path(a.data).read_bytes()).hexdigest()},indent=2))
    elif a.command=='evaluate':
        scores=[]
        for seed in range(10000,10000+a.episodes):
            s,_=env.reset(seed=seed); total=0
            for _ in range(200):
                s,r,t,tr,_=env.step(act(s)); total+=r
                if t or tr: break
            scores.append(total)
        result={'returns':scores,'mean':float(np.mean(scores)),'std':float(np.std(scores))}; print(result)
        (out/'evaluation.json').write_text(json.dumps(result,indent=2))
    else:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        log=json.loads((out/'loss.json').read_text()); plt.plot([x['update'] for x in log],[x['actor_loss'] for x in log]); plt.xlabel('updates'); plt.ylabel('actor loss'); plt.savefig(out/'loss.png')
    env.close()
if __name__=='__main__': main()
