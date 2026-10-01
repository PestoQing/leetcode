import math
from typing import List
# RNN 的前向传播公式
def rnn_cell_forward(x_t: List[float],
                     h_prev: List[float],
                     W_xh: List[float],
                     W_hh: List[float],
                     b_h: List[float]) -> List[float]:
    
    input_dim = len(x_t)
    hidden_dim = len(h_prev)
    res = []
    
    for i in range(hidden_dim):
        tmp = 0.0
        for j in range(input_dim):
            tmp += W_xh[j][i] * x_t[j]
        
        tmp1 = 0.0
        for j in range(hidden_dim):
            tmp1 += W_hh[j][i] * h_prev[j]
        
        tmp2 = tmp + tmp1 + b_h[i]
        res.append(math.tanh(tmp2))
        
    return res