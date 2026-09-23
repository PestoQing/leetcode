class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def construct(values):
    if not values or values[0] is None:
        return None

    root = TreeNode(values[0])
    nodes = [root]
    value_index = 1
    node_index = 0

    while node_index < len(nodes) and value_index < len(values):
        node = nodes[node_index]
        node_index += 1

        if value_index < len(values) and values[value_index] is not None:
            node.left = TreeNode(values[value_index])
            nodes.append(node.left)
        value_index += 1

        if value_index < len(values) and values[value_index] is not None:
            node.right = TreeNode(values[value_index])
            nodes.append(node.right)
        value_index += 1

    return root
