# Definition for a binary tree node.
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right
from typing import List, Optional
from binaryTree import TreeNode ,construct
class Solution:
    def postorderTraversal(self, root: Optional[TreeNode]) -> List[int]:
        res=[]
        def dfs(cur):
            if cur is None:
                return
            dfs(cur.left)
            dfs(cur.right)
            res.append(cur.val)

        dfs(root)
        return res

root = [1,None,2,3]

Root = construct(root)

print(Solution().postorderTraversal(Root))