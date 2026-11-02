"""真实更新集成测试：每轮仿真、优化器数值、离线边界、归档与加载一致性。"""
import hashlib
import unittest
from unittest.mock import patch

import torch
import live_engine


class LiveTests(unittest.TestCase):
    def test_all_algorithms_and_archives(self):
        for algo in ['bc','ppo','sac','iql']:
            with self.subTest(algo=algo):
                e=live_engine.Experiment(algo,seed=17,lr=.003)
                try:
                    baseline=e.history[0]
                    self.assertEqual(len(baseline['evaluation']['frames']),201)
                    self.assertEqual(e.evaluate(),baseline['evaluation'])
                    # 离线更新不得偷偷用训练环境采集新数据，评估环境独立创建。
                    if algo in ['bc','iql']:
                        e.env.step=lambda action: (_ for _ in ()).throw(AssertionError('离线训练调用了env.step'))
                        frozen=(e.folder/'frozen-data.npz').read_bytes()
                    for index in [1,2]:
                        before=e.actor_hash()
                        record=e.update()
                        self.assertEqual(record['round'],index)
                        self.assertEqual(record['previous_actor_hash'],before)
                        self.assertNotEqual(record['actor_hash'],before)
                        self.assertEqual(record['evaluation'],e.evaluate())
                        self.assertEqual(record['evaluation']['steps'],200)
                        self.assertAlmostEqual(sum(x['reward'] for x in record['evaluation']['frames']),record['evaluation']['return_'])
                        self.assertAlmostEqual(record['trace']['gradient_check']['difference'],0.,places=5)
                        for update in record['trace']['updates']:
                            self.assertAlmostEqual(update['after'],update['predicted_after'],places=6)
                            self.assertEqual(update['step'],index)
                        # 保存的模型必须能产生同样策略，而不是仅保存了网页动画。
                        saved=torch.load(e.folder/f'round-{index:03}.pt',weights_only=False)
                        clone=live_engine.Actor();clone.load_state_dict(saved['actor'])
                        s=torch.tensor([[1.,0.,0.],[0.,1.,2.]])
                        torch.testing.assert_close(clone.deterministic(s),e.actor.deterministic(s))
                    if algo in ['bc','iql']:
                        self.assertEqual((e.folder/'frozen-data.npz').read_bytes(),frozen)
                        self.assertEqual(len(e.buffer),2048)
                finally:e.close()

    def test_low_memory_guard(self):
        class Memory:
            available=1024
        with patch.object(live_engine.psutil,'virtual_memory',return_value=Memory()):
            with self.assertRaises(RuntimeError):live_engine.check_memory()


if __name__=='__main__':unittest.main()
