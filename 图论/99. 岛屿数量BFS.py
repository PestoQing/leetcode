from collections import deque


direction = [[0, 1], [1, 0], [0, -1], [-1, 0]]  # 四个方向：上、右、下、左


def bfs(grid, x, y):
	"""
	对一块陆地进行广度优先遍历并沉没
	"""
	# 将起点沉没并加入队列，避免重复访问
	queue = deque([(x, y)])
	grid[x][y] = 0

	while queue:
		current_x, current_y = queue.popleft()
		for i, j in direction:
			next_x = current_x + i
			next_y = current_y + j
			# 下标越界，跳过：
			#   next_x < 0              —— 越过上边界
			#   next_x >= len(grid)     —— 越过下边界
			#   next_y < 0              —— 越过左边界
			#   next_y >= len(grid[0])  —— 越过右边界
			#   四项用 or 连接：任一成立即越界；从左到右短路求值，前项成立就不再检查后项，
			#   因此后面的 grid[next_x][next_y] 只会在下标合法时才被访问
			if next_x < 0 or next_x >= len(grid) or next_y < 0 or next_y >= len(grid[0]):
				continue
			# 未搜索的陆地，沉没并加入队列
			if grid[next_x][next_y] == 1:
				grid[next_x][next_y] = 0
				queue.append((next_x, next_y))


if __name__ == '__main__':
	n, m = map(int, input().split())

	# 邻接矩阵
	grid = []
	for i in range(n):
		grid.append(list(map(int, input().split())))

	res = 0
	for i in range(n):
		for j in range(m):
			# 当前节点是未搜索的陆地，岛屿数量加一并使用 BFS 沉没整座岛屿
			if grid[i][j] == 1:
				res += 1
				bfs(grid, i, j)

	print(res)
