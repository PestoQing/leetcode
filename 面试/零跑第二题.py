def solution(N: int) -> int:
    MOD = 10**9 + 7
    
    # 初始化前三个状态：f(0), f(1), f(2)
    # f(0) = 1 (空序列，用于推导)
    # f(1) = 0, f(2) = 0 (无法由 >= 3 的数组成)
    dp = [1, 0, 0]
    
    # 如果 N 小于 3，直接返回对应的初始值
    if N < 3:
        return dp[N]
        
    # 从 i = 3 开始动态计算，边算边 append
    for i in range(3, N + 1):
        # 状态转移方程：f(n) = f(n-1) + f(n-3)
        # dp[-1] 就是 f(i-1)，dp[-3] 就是 f(i-3)
        current_val = (dp[-1] + dp[-3]) % MOD
        dp.append(current_val)
        
    # 最后返回 dp[N]
    return dp[N]