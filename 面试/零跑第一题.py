from typing import List

def solution(grid: List[List[int]], x: int, y: int) -> int:
    dp = []
    
    # i 代表垂直方向（行 y），j 代表水平方向（列 x）
    for i in range(y + 1):
        row = []
        for j in range(x + 1):
            if i == 0 and j == 0:
                # 起点
                row.append(grid[0][0])
            elif i == 0:
                # 第一行，只能从左边走过来
                row.append(row[-1] + grid[i][j])
            elif j == 0:
                # 第一列，只能从上边走下来
                # dp[-1][0] 就是上一行的第一个元素
                row.append(dp[-1][0] + grid[i][j])
            else:
                # 状态转移：上方 dp[-1][j] 和左方 row[-1] 取最小值
                row.append(min(dp[-1][j], row[-1]) + grid[i][j])
                
        dp.append(row)
        
    # 返回最终到达 (y, x) 的最小路径和
    return dp[-1][-1]