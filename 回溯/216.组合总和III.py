from typing import List
class Solution:
    def combinationSum3(self, k: int, n: int) -> List[List[int]]:
        tmp=[]
        res=[]
        
        self.back(k,n,tmp,res,1)
        return res
    
    def back(self,k,n,tmp,res,start):
        if sum(tmp)>n:
            return
        if len(tmp)==k:
            if sum(tmp) == n :
                res.append(tmp[:])
            
            return 
        for i in range(start,10):
            tmp.append(i)
            self.back(k,n,tmp,res,i+1)
            tmp.pop()

k = 3
n = 7
print(Solution().combinationSum3(k,n))