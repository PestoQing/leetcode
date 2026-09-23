class Solution:
    def reverseString(self, s: list[str]) -> None:
        """
        Do not return anything, modify s in-place instead.
        """
        head, tail = 0,len(s)-1
        while head < tail:
            tmp = s[head]
            s[head] = s[tail]
            s[tail] = tmp
            head +=1
            tail -=1
s = ["h","e","l","l","o"]
Solution().reverseString(s)
print(s)        