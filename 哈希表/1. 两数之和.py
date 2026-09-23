class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = set()
        for i in range(len(nums)):
            left = target - nums[i]
            if left in seen:
                return[nums.index(left),i]
            seen.add(nums[i])
        return 

# 定义空集合
numbers = set()
# 定义集合
numbers = {1, 2, 3, 3}

print(numbers)  # {1, 2, 3}
# 定义空字典
numbers = {}
student = dict(name="Tom", age=18)

nums = [2,7,11,15]
target = 9