from typing import List
class Solution:
    def generateMatrix(self, n: int) -> list[list[int]]:
        res=[[0]*n for _ in range(n)]
        count = 1
        layer = 0
        if n % 2 == 1:
            res[(n-1)//2][(n-1)//2]=n*n
            while n >1:
                for i in range(n-1):
                    res[layer][i+layer] = count
                    count+=1
                for i in range(n-1):
                    res[i+layer][n-1] = count
                    count+=1
                for i in range(n-1):
                    res[n-1+layer][n-1-i-layer] = count
                    count+=1
                for i in range(n-1):
                    res[n-1-i-layer][layer] = count
                    count+=1
                n=n-2
                layer+=1
            

        return res

print(Solution().generateMatrix(5))