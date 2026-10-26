direction = [[0, 1], [1, 0], [0, -1], [-1, 0]]  # 四个方向：上、右、下、左


def dfs(grid, x, y):
    """
    对一块陆地进行深度优先遍历并标记
    """
    for i, j in direction:
        next_x = x + i
        next_y = y + j
        # 下标越界，跳过：
        #   next_x < 0              —— 越过上边界
        #   next_x >= len(grid)     —— 越过下边界
        #   next_y < 0              —— 越过左边界
        #   next_y >= len(grid[0])  —— 越过右边界
        #   四项用 or 连接：任一成立即越界；从左到右短路求值，前项成立就不再检查后项，
        #   因此后面的 grid[next_x][next_y] 只会在下标合法时才被访问
        if next_x < 0 or next_x >= len(grid) or next_y < 0 or next_y >= len(grid[0]):
            continue
        # 未搜索的陆地，沉没并继续深度优先搜索
        if grid[next_x][next_y] == 1:
            grid[next_x][next_y] = 0
            dfs(grid, next_x, next_y)


if __name__ == '__main__':  
    # 版本一
    n, m = map(int, input().split())
    
    # 邻接矩阵
    grid = []
    for i in range(n):
        grid.append(list(map(int, input().split())))
    
    res = 0
    for i in range(n):
        for j in range(m):
            # 判断：如果当前节点是陆地，res+1并标记访问该节点，使用深度搜索标记相邻陆地。
            if grid[i][j] == 1:
                res += 1
                grid[i][j] = 0
                dfs(grid, i, j)
    
    print(res)