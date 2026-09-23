from ListNode import ListNode, constructListNode
class Solution:
    def removeElements(self, head: ListNode | None, val: int) -> ListNode | None:
        dummy = ListNode()
        dummy.next = head
        curr = dummy

        while curr.next is not None:
            if curr.next.val == val:
                curr.next = curr.next.next
            else:
                curr = curr.next

        return dummy.next

nums = [1,2,6,3,4,5,6]
val = 6
head = constructListNode(nums)
curr=Solution().removeElements(head,val)
while curr is not None:
    print(curr.val)
    curr=curr.next