class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        
        if not s:
            return 0
        
        # 字典，记录当前对应的左边的字母是几号
        last_seen = {}
        left = 0
        max_len = 0
        
        for right in range(len(s)):
            current = s[right]

            if current in last_seen:
                old_index = last_seen[current]

                for index in range(left, old_index + 1):
                    del last_seen[s[index]]

                left = old_index + 1

            last_seen[current] = right
            max_len = max(max_len, right - left + 1)
            
        return max_len
