from types import List
class Solution:
    def threeSum(self, nums: List[int]) -> List[List[int]]:
        nums=sorted(nums)
        i=0
        set1=set()
        n=len(nums)
        right=n-1
        for i in range(len(nums)-2):
            left=i+1
            right=len(nums)-1
            while left!=right:
                sum=nums[i]+nums[left]+nums[right]
                if sum>0 and left==i+1:
                    n-=1                
                if sum>0 :
                    right-=1

                elif sum==0:
                    set1.add((nums[i],nums[left],nums[right]))
                    right-=1
                    
                elif sum<0:
                    left+=1
            # if left==right:
            #     i+=1
            
            
        return [list(x) for x in set1]