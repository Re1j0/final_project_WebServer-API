def f(s, e):
    if s > e or s == 81: return 0
    elif s == e: return 1
    else: return f(s + s // 10, e) + f(s + 3, e) + f(2 * s - 1, e)

print(f(42, 73) * f(73, 89))