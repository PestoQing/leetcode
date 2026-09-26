class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        
        if not s:
            return 0
        
        # 哈希表：记录元素最近一次出现的下标
        last_seen = {}
        left = 0
        max_len = 0
        
        for right in range(len(s)):
            current = s[right]
            
            # 如果当前元素在窗口内出现过，移动左指针
            if current in last_seen and last_seen[current] >= left:
                left = last_seen[current] + 1
                
            # 更新当前元素的最新下标
            last_seen[current] = right
            
            # 计算当前窗口长度并更新最大值
            max_len = max(max_len, right - left + 1)
            
        return max_len

# 测试
s = [1, 3, 5, 7, 9]
print(Solution().lengthOfLongestSubstring(s)) # 输出 5