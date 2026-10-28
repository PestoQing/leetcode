from copy import deepcopy
# # n 条轨迹，
# # (s, c) {(s1, c1), ...， (sn, cn)} cost 越小越好
# # 选一条最好的轨迹
# # 1. 排除掉一些 (si >= sj, ci >= cj) i 肯定比 j 更差， 把 i 排除；
# # 求所有满足上述条件排除之后剩下的轨迹集合
candidate=([1,2], [2,1],[1,1], [3,3])
tmp=[]
tmp = deepcopy(candidate)

# for a in candidate:
#     b=a[0]
#     c=a[1]
#     d=[]
#     d.append(b)
#     d.append(c)
#     tmp.append(d)

res=[]

j=2
    
for  i in range(len(candidate)):
    
    if i == j:
        res.append([tmp[i][0],tmp[i][1]])
        continue    
    flag =  not (
            tmp[i][0] >= tmp[j][0]
            and tmp[i][1] >= tmp[j][1]
        )
    if flag:
        res.append([tmp[i][0],tmp[i][1]])
        

print(res)
