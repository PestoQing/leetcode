from typing import List
class Solution:
    def generateMatrix(self, n: int) -> list[list[int]]:
        res=[[0]*n for _ in range(n)]
        count = 1
        layer = 0
        tmp= n
        if n % 2 == 1:
            res[(n-1)//2][(n-1)//2]=n*n
            while n >1:
                for i in range(n-1):
                    res[layer][i+layer] = count
                    count+=1
                for i in range(n-1):
                    res[i+layer][tmp-1 -layer] = count
                    count+=1
                for i in range(n-1):
                    res[tmp-1-layer][tmp-1-i-layer] = count
                    count+=1
                for i in range(n-1):
                    res[tmp-1-i-layer][layer] = count
                    count+=1
                n=n-2
                layer+=1
            
        else:

   
            while n >1:
                for i in range(n-1):
                    res[layer][i+layer] = count
                    count+=1
                for i in range(n-1):
                    res[i+layer][tmp-1 -layer] = count
                    count+=1
                for i in range(n-1):
                    res[tmp-1-layer][tmp-1-i-layer] = count
                    count+=1
                for i in range(n-1):
                    res[tmp-1-i-layer][layer] = count
                    count+=1
                n=n-2
                layer+=1

        return res

print(Solution().generateMatrix(4))