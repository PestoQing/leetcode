class Solution:
    def removeElement(self, nums: list[int], val: int) -> int:
        slow,fast=0,0
        for i in range(len(nums)):
            if nums[fast] != val:
                nums[slow]= nums[fast]
                slow+=1
            fast +=1
                

        return slow ,nums

nums = [3,2,2,3]
val = 3
print(Solution().removeElement(nums,val))