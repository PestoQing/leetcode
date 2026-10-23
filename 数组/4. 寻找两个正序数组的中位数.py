class Solution:
    def findMedianSortedArrays(self, nums1: list[int], nums2: list[int]) -> float:
        a=len(nums1)
        b=len(nums2)
        half_a=(a-1)//2
        half_b=(b-1)//2
        all=a+b
        half_all=(all-1)//2
        if a==0:
            if b%2==0:
                return (nums2[half_all]+nums2[half_all+1])/2
            else:
                return nums2[half_all]
        elif b==0:
            if a%2==0:
                return (nums1[half_all]+nums1[half_all+1])/2
            else:
                return nums1[half_all]
        # 两个数组都只有一个元素：直接对这两个数取平均。
        elif a==1 and b==1:
            return (nums2[0]+nums1[0])/2

        cnt=0
        if nums1[half_a]<=nums2[half_b]:
            cnt=half_a-1
            i=half_a
            j=0
        else:
            cnt=half_b-1
            i=0
            j=half_b
        if all % 2 ==1:

            while 1:
                # 三项同时成立：i 未越界、j 未越界，且 nums1 当前值不大于 nums2 当前值。
                # and 从左到右短路判断，先确认下标有效，再比较数组元素。
                if i<a and j<b and nums1[i]<=nums2[j] :
                    res=nums1[i]
                    i +=1

                # 两个下标都有效，且 nums2 当前值更小，因此本次从 nums2 取数。
                elif i<a and j<b and nums1[i]>nums2[j] :
                    res=nums2[j]
                    j +=1
                elif i>=a:

                    res=nums2[j]
                    j +=1
                elif j>=b:

                    res=nums1[i]
                    i +=1
                cnt +=1
                if cnt == half_all:
                    return res
        else:
            while 1:
                # 三项同时成立：i 未越界、j 未越界，且 nums1 当前值不大于 nums2 当前值。
                # and 从左到右短路判断，先确认下标有效，再比较数组元素。
                if i<a and j<b and nums1[i]<=nums2[j] :
                    res=nums1[i]
                    i +=1

                # 两个下标都有效，且 nums2 当前值更小，因此本次从 nums2 取数。
                elif i<a and j<b and nums1[i]>nums2[j] :
                    res=nums2[j]
                    j +=1
                elif i>=a:
                    flag = 1
                    res=nums2[j]
                    j +=1
                elif j>=b:
                    flag=2
                    res=nums1[i]
                    i +=1

                cnt +=1
                if cnt==half_all:
                    tmp=res
                if cnt == half_all+1:
                    return (res+tmp)/2




nums1 = [1,3]
nums2 = [2]
print(Solution().findMedianSortedArrays(nums1,nums2))
