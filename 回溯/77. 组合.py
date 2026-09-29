class Solution:
    def back(self,n,k,start,res,path):
        if len(path)==k:
            res.append(path[:])
            return
        for i in range(start,n+1):
            path.append(i)
            self.back(n,k,i+1,res,path)
            path.pop()
         
    def combine(self, n: int, k: int) -> list[list[int]]:
        res=[]
        path=[]
        self.back(n,k,1,res,path)
        return res


n = 4
k = 2
print(Solution().combine(n,k))