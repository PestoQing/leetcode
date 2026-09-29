def sqrt_by_gradient_descent(y):
    assert y > 0
    x = 1.0          # 初始值设为 1
    arr = []
    
    for i in range(10000):  # 1万次循环足够
        arr.append(x)
        
        # 核心修正：x**3 改为 x**2
        lr = 1.0 / (y + x**2 + 1)
        
        x -= lr * x * (x**2 - y)
        
    return x  # 【缩进完美，成功移出循环】
value = 10000000
res=sqrt_by_gradient_descent(value)
print(res) 
ValueError = value -res**2
print(f"误差：{ValueError}")