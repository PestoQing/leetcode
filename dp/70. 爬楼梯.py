class Solution:
    def climbStairs(self, n: int) -> int:
        if n == 0 :
            return 0
        elif  n == 1:
            return 1
        elif n == 2:
            return 2
        else:
            dp = [0,1,2]
            for i in range(3,n+1):
                dp.append(dp[i-1]+dp[i-2])
        return dp[-1]

print(Solution().climbStairs(3))