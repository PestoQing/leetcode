from typing import List
class Solution:
    def minSubArrayLen(self, target: int, nums: list[int]) -> int:
        start,end = 0,0
        res = float('inf')
        def list_sum(start,end):
            sum = 0
            for i in range(start,end+1):
                sum+=nums[i]
            return sum
        while end <= len(nums)-1:
            while list_sum(start,end) <target:
                end+=1
            while list_sum(start,end)>=target:
                start+=1
            res = min(end - start +1 ,res) 
            
            

        return res

target = 7
nums = [2,3,1,2,4,3]
print(Solution().minSubArrayLen(target,nums))