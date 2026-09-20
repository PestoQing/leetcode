from typing import List
class Solution:
    def sortedSquares(self, nums: List[int]) -> List[int]:
        # for i in range(len(nums)):
        #     nums[i]=nums[i]*nums[i]
        # nums.sort()
        # return nums
        head = 0
        tail = len(nums)-1
        res = [0]*len(nums)
        for i in reversed(range(len(nums))):
            if abs(nums[head])>abs(nums[tail]):
                res [i] = nums[head] *nums[head]
                head+=1
            else:
                res[i] = nums[tail] * nums[tail]
                tail -=1
        return res

nums = [-4,-1,0,3,10]
print(Solution().sortedSquares(nums))