from typing import List
from collections import deque
class Solution:
    def findContentChildren(self, g: List[int], s: List[int]) -> int:
        if len(s) == 0:
            return 0
        g.sort()
        s.sort()
        g=deque(g)
        s=deque(s)
        a=100
        a=int(a)
        index = 0
        while len(g) >0 and len(s)>0:
            a=g.popleft()
            b=s.popleft()
            while a>b and len(s)>0:
                b=s.popleft()
            if a<=b:
                index+=1
                continue
            else:
                break
        return index


g = [10,9,8,7]
s = [5,6,7,8]
print(Solution().findContentChildren(g,s))