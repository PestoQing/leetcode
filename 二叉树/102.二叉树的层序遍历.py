# Definition for a binary tree node.
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right
from typing import List
from binaryTree import TreeNode,construct
from collections import deque
class Solution:
    def levelOrder(self, root: TreeNode | None) -> List[List[int]]:
        if root is None:
            return []
        cur = root
        tmp =deque()
        tmp.append(cur)
        res=[]
        while len(tmp) !=0:
            level = []
            for i in range(len(tmp)):
                cur=tmp.popleft()
                
                level.append(cur.val)
                
                if cur.left is not None:
                    tmp.append(cur.left)
                if cur.right is not None:
                    tmp.append(cur.right)
            res.append(level)
        
        return res

root = [3,9,20,None,None,15,7]
root = construct(root)
print(Solution().levelOrder(root))
        