from ListNode import ListNode ,constructListNode
class Solution:
    def addTwoNumbers(self, l1: ListNode | None, l2: ListNode | None) -> ListNode | None:
        dummy = ListNode(0)
        node = dummy
        cnt = 0
        while l1 or l2 or cnt:
            if l1 is None:
                a=0
            else:
                a=l1.val
            if l2 is None:
                b=0
            else:
                b=l2.val
            sum = a+b+cnt
            node.next = ListNode(sum%10)
            node = node.next
            if sum>=10:
                cnt = 1
            else:
                cnt =0
            if l1:
                l1=l1.next
            if l2:
                l2=l2.next
        return dummy.next 
l1 = constructListNode([9,9,9,9,9,9])
l2 = constructListNode([5,6,4])
print(Solution().addTwoNumbers(l1,l2))