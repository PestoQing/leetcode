"""self 的常见用法示例。

直接运行本文件即可观察输出：
    python self_examples.py
"""


class Student:
    # 类属性：属于 Student 类，所有对象默认都可以读取
    school = "一中"

    def __init__(self, name, age):
        # self 表示当前正在创建的对象
        # 这两行给每个对象创建各自独立的实例属性
        self.name = name
        self.age = age

    # def __str__(self):
    #     # print(self) 默认会显示类型和内存地址
    #     # 定义 __str__ 后，可以自定义 print(self) 的显示内容
    #     return f"Student(name={self.name}, age={self.age})"

    def introduce(self):
        # self 代表整个 Student 对象
        print("整个对象：", self)

        # 读取当前对象的实例属性
        print(f"我叫 {self.name}，今年 {self.age} 岁")

        # self.school：先找对象自己的 school，找不到再找类的 school
        print(f"我在 {self.school} 上学")

    def grow(self, years):
        # 修改当前对象自己的 age，不会影响其他 Student 对象
        self.age += years

    def change_school(self, school):
        # 这里的 school 是方法参数，self.school 是对象属性
        # 等号左边必须写 self.school，才能保存到当前对象中
        self.school = school

    def get_summary(self):
        # 方法可以返回使用 self 组合出的结果
        return f"{self.name}-{self.age}"

    def say_to(self, other):
        # self 是说话的人，other 是传进来的另一个对象
        print(f"{self.name} 对 {other.name} 说：你好！")

    def introduce_again(self):
        # 在一个实例方法中调用同一个对象的另一个实例方法
        # 不写 self 就会被当成普通函数查找
        self.introduce()


class Counter:
    def __init__(self):
        # 每个 Counter 对象都有自己的 count
        self.count = 0

    def add(self):
        self.count += 1


class Team:
    def __init__(self, name):
        self.name = name
        # 可变对象也应该放在 __init__ 中
        # 这样每个 Team 都有自己的 members 列表
        self.members = []

    def add_member(self, member):
        self.members.append(member)
        # 返回 self，可以继续调用当前对象的方法
        return self

    def show(self):
        print(f"{self.name} 的成员：{self.members}")
        return self


def main():
    print("=== 1. self 代表当前对象 ===")
    student1 = Student("小明", 18)
    student2 = Student("小红", 19)
    print("直接 print(student1)：", student1)
    print("student1 的对象地址：", id(student1))
    print("student2 的对象地址：", id(student2))
    student1.introduce()
    student2.introduce()

    print("\n=== 2. self 让每个对象拥有独立属性 ===")
    student1.grow(1)
    student1.introduce()
    student2.introduce()  # student2 的年龄不受影响

    print("\n=== 3. 方法参数和 self.属性可以同名 ===")
    student1.change_school("二中")
    print("student1.school：", student1.school)
    print("student2.school：", student2.school)
    print("Student.school：", Student.school)

    print("\n=== 4. self 调用其他实例方法 ===")
    student1.introduce_again()
    student1.say_to(student2)

    print("\n=== 5. self 访问另一个对象 ===")
    print("student1 的摘要：", student1.get_summary())

    print("\n=== 6. 不同对象的计数器互不影响 ===")
    counter1 = Counter()
    counter2 = Counter()
    counter1.add()
    counter1.add()
    counter2.add()
    print("counter1.count：", counter1.count)
    print("counter2.count：", counter2.count)

    print("\n=== 7. return self 实现链式调用 ===")
    team = Team("后端小组")
    team.add_member("小明").add_member("小红").show()


if __name__ == "__main__":
    main()
