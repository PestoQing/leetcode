from typing import List
class Solution:
    def minSubArrayLen(self, target: int, nums: list[int]) -> int:
        start,end = 0,0
        res = float('inf')
        sum_=nums[0]
        while end<=len(nums)-1:

            while sum_<target :
                end+=1
                if end>len(nums)-1:
                    if res == float('inf'):
                        return 0
                    return res
                sum_ += nums[end]
            # res=min(res,end-start+1)
            while sum_ >= target:
                sum_ -= nums[start]
                start +=1
            res=min(res,end-start+1+1)
        if res == float('inf'):
            return 0
        return res

target = 7
nums = [2,3,1,2,4,3]
print(Solution().minSubArrayLen(target,nums))