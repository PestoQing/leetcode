class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def constructListNode(nums):
    dummy = ListNode()
    current = dummy

    for num in nums:
        current.next = ListNode(num)
        current = current.next

    return dummy.next