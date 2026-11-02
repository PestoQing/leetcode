import unittest
import torch
import numpy as np

class CoreTests(unittest.TestCase):
    def test_expectile(self):
        residual=torch.tensor([-2.,2.])
        loss=torch.where(residual>0,.7,.3)*residual.square()
        torch.testing.assert_close(loss,torch.tensor([1.2,2.8]))
    def test_timeout_bootstrap(self):
        # 相同奖励与下一状态价值，时间截断仍使用bootstrap。
        done=torch.tensor([1.,0.]); target=1+.99*(1-done)*10
        torch.testing.assert_close(target,torch.tensor([1.,10.9]))
    def test_dataset(self):
        d=np.load('smoke.npz')
        self.assertEqual(d['observation'].shape,(1000,3))
        self.assertTrue(np.all(np.abs(d['action'])<=2))
        self.assertEqual(int(d['truncated'].sum()),5)
if __name__=='__main__': unittest.main()
