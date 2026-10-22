class Solution:
    def findMedianSortedArrays(self, nums1: list[int], nums2: list[int]) -> float:
        res=-1
        a=len(nums1)
        b=len(nums2)
        half_a=(a-1)//2
        half_b=(b-1)//2
        all=a+b
        if all % 2 ==1:
            half_all=(all-1)//2
            cnt=0
            if nums1[half_a]<=nums2[half_b]:
                cnt=half_a
                i=half_a+1
                j=0
            else:
                cnt=half_b
                i=0
                j=half_b+1
            
            while 1:
                if nums1[i]<=nums2[j]:
                    i +=1
                else:
                    j+=1
                cnt +=1
               
                    

        return res

nums1 = [1,2,3,4,5] 
nums2 = [3,4,5,6]
print(Solution().findMedianSortedArrays(nums1,nums2))