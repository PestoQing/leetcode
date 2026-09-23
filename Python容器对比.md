# Python 列表、字典、集合和哈希表对比

| 类型 | 定义 | 添加元素 | 查找方式 | 是否允许重复 | 是否有序 |
|---|---|---|---|---|---|
| 列表 `list` | `[1, 2, 3]` | `append()` | 按下标或遍历 | 允许 | 有序 |
| 字典 `dict` | `{"a": 1}` | `dict[key] = value` | 按键 | 键不重复 | 保持插入顺序 |
| 集合 `set` | `{1, 2, 3}` | `add()` | 按元素 | 不允许 | 无下标顺序 |

## 1. 列表 `list`

```python
numbers = [1, 2, 3]

numbers.append(4)       # 添加一个元素
numbers.extend([5, 6])  # 添加多个元素
numbers.insert(0, 100)  # 指定位置添加

print(numbers[0])       # 按下标访问
```

列表允许重复：

```python
numbers.append(3)
# [1, 2, 3, 4, 5, 6, 3]
```

常见操作：

```python
numbers.remove(3)  # 删除第一个值为 3 的元素
numbers.pop()      # 删除并返回最后一个元素
3 in numbers      # 判断元素是否存在
numbers.index(4)   # 查找元素下标
```

## 2. 字典 `dict`

```python
student = {
    "name": "Tom",
    "age": 18
}

student["score"] = 95  # 添加键值对
student["age"] = 19    # 修改已有键对应的值
```

字典通过**键**查找：

```python
print(student["name"])  # Tom
```

常见操作：

```python
student.get("name")       # 获取值，键不存在时不会报错
student.keys()            # 获取所有键
student.values()          # 获取所有值
student.items()           # 获取所有键值对
student.pop("age")        # 删除指定键
```

字典的键不能重复：

```python
data = {"a": 1, "a": 2}
print(data)  # {'a': 2}
```

后面的值会覆盖前面的值。

## 3. 集合 `set`

```python
numbers = {1, 2, 3}

numbers.add(4)          # 添加一个元素
numbers.update([5, 6])  # 添加多个元素
```

集合自动去重：

```python
numbers.add(3)
print(numbers)  # {1, 2, 3, 4, 5, 6}
```

常见操作：

```python
numbers.remove(2)  # 删除元素，不存在会报错
numbers.discard(2) # 删除元素，不存在也不会报错
4 in numbers       # 判断元素是否存在
```

集合不能通过下标访问：

```python
numbers[0]  # 错误
```

## 主要区别

```python
# 列表：保存一组有顺序的数据
items = ["a", "b", "a"]

# 字典：保存键和值的对应关系
prices = {"apple": 5, "banana": 3}

# 集合：保存不重复的数据，适合快速判断是否存在
visited = {"Tom", "Jerry"}
```

在算法中通常这样选择：

- 需要按位置访问：使用列表
- 需要通过键快速找到对应值：使用字典
- 只关心元素是否存在、并且需要去重：使用集合
- `dict` 和 `set` 底层都使用哈希表，查找、添加通常约为 $O(1)$
- 列表按下标访问约为 $O(1)$，但查找某个值通常是 $O(n)$