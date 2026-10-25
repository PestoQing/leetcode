class Solution:
    def maxArea(self, height: list[int]) -> int:
        left=0
        right=len(height)-1
        res=-1
        while left<right:
            tmp=min(height[left],height[right])*(right-left)
            res=max(tmp,res)
            if height[left]<=height[right]:
                left+=1
            else:
                right-=1


        return res
    
height=[1,8,6,2,5,4,8,3,7]
print(Solution().maxArea(height))