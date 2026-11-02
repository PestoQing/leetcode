"""完整实验矩阵：串行、资源受限、失败即停止，不自动重试。"""
import subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent

def run(*args):
    subprocess.run([str(ROOT/'run.sh'),*map(str,args)],cwd=ROOT,check=True)

def main():
    base=ROOT/'runs'/'curriculum'
    if base.exists(): raise RuntimeError('实验目录已存在；请先审核已有结果，不自动覆盖或恢复')
    base.mkdir(parents=True)
    datasets=[]
    for seed in range(3):
        for algo,steps in [('ppo',300000),('sac',75000)]:
            out=base/f'{algo}-{seed}'
            run('train','--algo',algo,'--steps',steps,'--seed',seed,'--out',out)
            run('evaluate','--algo',algo,'--model',out/'model.zip','--out',out,'--video')
    # 采用 seed0 的中途策略；继续训练另一个75000步需保留优化器与经验池，
    # 此处完整150000步独立重训，明确区分来源，不伪称连续checkpoint。
    final=base/'sac-final'
    run('train','--algo','sac','--steps',150000,'--out',final)
    for name,model in [('random',None),('medium',base/'sac-0'/'model.zip'),('final',final/'model.zip')]:
        file=base/f'{name}.npz'; args=['collect','--steps',20000,'--data',file,'--out',base/name]
        if model: args+=['--model',model]
        run(*args); datasets.append(file)
    loaded=[np.load(x) for x in datasets]
    mixed=base/'mixed.npz'; np.savez_compressed(mixed,**{k:np.concatenate([d[k] for d in loaded]) for k in loaded[0].files})
    for seed in range(3):
        for algo,steps in [('bc',20000),('iql',50000)]:
            out=base/f'{algo}-{seed}'
            run('train','--algo',algo,'--steps',steps,'--seed',seed,'--data',mixed,'--out',out)
            run('evaluate','--algo',algo,'--model',out/'model.pt','--out',out,'--video')
            run('plot','--out',out)
    for algo,steps in [('bc',20000),('iql',50000)]:
        out=base/f'{algo}-medium'
        run('train','--algo',algo,'--steps',steps,'--data',datasets[1],'--out',out)
        run('evaluate','--algo',algo,'--model',out/'model.pt','--out',out)
if __name__=='__main__': main()
