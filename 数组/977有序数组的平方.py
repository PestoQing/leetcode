class Solution:
    def sortedSquares(self, nums: List[int]) -> List[int]:
        # for i in range(len(nums)):
        #     nums[i]=nums[i]*nums[i]
        # nums.sort()
        # return nums
        head = 0
        tail = len(nums)-1
        while head <=tail:
            if abs(nums[head])<abs(nums[tail]):
                res

nums = [-4,-1,0,3,10]
print(Solution().sortedSquares(nums))