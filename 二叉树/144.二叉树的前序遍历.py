from typing import List, Optional
from binaryTree import TreeNode, construct

class Solution:
    def preorderTraversal(self, root: Optional[TreeNode]) -> List[int]:
        res = []
        def dfs(node):
            if node is None:
                return
            res.append(node.val)
            dfs(node.left)
            dfs(node.right)
        
        dfs(root)
        return res

root = [1,None,2,3]

Root = construct(root)
print(Solution().preorderTraversal(Root))