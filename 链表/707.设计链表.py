from ListNode import ListNode, constructListNode
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class MyLinkedList:

    def __init__(self):
        self.dummy_head = ListNode()
        self.size = 0

    def get(self, index: int) -> int:
        if index>=self.size or index<0:
            return -1
        curr = self.dummy_head
        for _ in range(index+1):
            curr = curr.next
        return curr.val

    def addAtHead(self, val: int) -> None:
        self.dummy_head.next = ListNode(val,self.dummy_head.next)
        self.size +=1


    def addAtTail(self, val: int) -> None:
        curr = self.dummy_head
        for _ in range(self.size):
            curr = curr.next
        curr.next = ListNode(val,None)
        self.size+=1
#  dummy 0 1 2   
#  size = 3 index =3
#  0 1 2 curr -> 2
#  size = 3 index =2
#  0 1 2 curr -> 1
    def addAtIndex(self, index: int, val: int) -> None:
        if index>self.size:
            return None
        curr = self.dummy_head
        for _ in range(index):
            curr = curr.next
        if index < self.size: 
            curr.next = ListNode(val,curr.next)
        else:
            curr.next = ListNode(val,None)
        self.size+=1

    def deleteAtIndex(self, index: int) -> None:
        if index>=self.size:
            return None
        curr = self.dummy_head
        for _ in range(index):
            curr = curr.next
        curr.next = curr.next.next
        self.size -=1

    def addAtHead(self, val: int) -> None:
        self.dummy_head.next = ListNode(val,self.dummy_head.next)
        self.size +=1


    def addAtTail(self, val: int) -> None:
        curr = self.dummy_head
        for _ in range(self.size):
            curr = curr.next
        curr.next = ListNode(val,None)
        self.size+=1
#  dummy 0 1 2   
#  size = 3 index =3
#  0 1 2 curr -> 2
#  size = 3 index =2
#  0 1 2 curr -> 1
    def addAtIndex(self, index: int, val: int) -> None:
        if index>self.size:
            return None
        curr = self.dummy_head
        for _ in range(index):
            curr = curr.next
        if index < self.size: 
            curr.next = ListNode(val,curr.next)
        else:
            curr.next = ListNode(val,None)
        self.size+=1

    def deleteAtIndex(self, index: int) -> None:
        if index>=self.size:
            return None
        curr = self.dummy_head
        for _ in range(index):
            curr = curr.next
        curr.next = curr.next.next
        self.size -=1


        


# Your MyLinkedList object will be instantiated and called as such:
obj = MyLinkedList()
val= 1
index= 2
param_1 = obj.get(index)
obj.addAtHead(val)
curr = obj.dummy_head.next
while curr is not None:
    print(curr.val)
    curr=curr.next
obj.addAtTail(val)
curr = obj.dummy_head.next
while curr is not None:
    print(curr.val)
    curr=curr.next
val =2

obj.addAtIndex(index,val)
print()
curr = obj.dummy_head.next
while curr is not None:
    print(curr.val)
    curr=curr.next

obj.addAtTail(3)
print()
curr = obj.dummy_head.next
while curr is not None:
    print(curr.val)
    curr=curr.next
val =2

obj.deleteAtIndex(index)
curr = obj.dummy_head.next
print()
while curr is not None:
    print(curr.val)
    curr=curr.next