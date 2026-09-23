import sys
# sys.stdin = open("input58.txt",'r')
n = int(input())
nums=[]
for _ in range(n):
    nums.append(int(input()))
print(nums)
qianzhouhe=[0]*len(nums)
qianzhouhe[0]=nums[0]
for i in range(1,n):
    qianzhouhe[i]=nums[i]+qianzhouhe[i-1]

while 1:
    try:
        line = input()
    
    except EOFError:
        break
    start, end = map(int,line.split())
    if start == 0:
        start_sum = 0
    else:
        start_sum = qianzhouhe[start-1]
    end_sum = qianzhouhe[end]

    print(end_sum-start_sum)

