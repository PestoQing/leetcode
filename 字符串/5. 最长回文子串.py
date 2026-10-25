class Solution:
    def longestPalindrome(self, s: str) -> str:
        n = len(s)
        if n < 2:
            return s
        
        res = ""
        # 创建二维数组 dp，初始化为 False
        # dp[i][j] 表示 s[i:j+1] 是否为回文串
        dp = [[False] * n for _ in range(n)]
        
        # 外层循环枚举子串长度
        for length in range(1, n + 1):
            # 内层循环枚举左边界 i
            # j 是右边界，公式为 j = i + length - 1
            # 循环条件 i + length - 1 < n (等同于 C++ 的 <= n - 1)
            for i in range(n - length + 1):
                j = i + length - 1
                
                if length == 1:
                    dp[i][j] = True
                elif length == 2:
                    dp[i][j] = (s[i] == s[j])
                else:
                    dp[i][j] = (dp[i + 1][j - 1] and s[i] == s[j])
                
                # 如果当前子串是回文，且长度大于已记录的结果
                if dp[i][j] and length > len(res):
                    res = s[i : i + length] # Python 切片是左闭右开，正好对应 substr(i, len)
                    
        return res