class Solution:
    def fib(self, n: int) -> int:
        if n == 0 :
            return 0
        elif  n == 1:
            return 1
        else:
            dp = [1,1]
            for i in range(2,n):
                dp.append(dp[i-1]+dp[i-2])
        return dp[-1]

print(Solution().fib(5))