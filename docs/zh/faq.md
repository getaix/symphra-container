# 常见问题（FAQ）

## 解析失败：ServiceNotFoundError
- 检查是否已注册对应类型或泛型键
- 对于 `Optional[T]`，未注册时不会抛错

## 循环依赖如何定位？
- 使用诊断工具与依赖图可视化（见「API 参考」中的 `visualization` 模块）

## 异步服务如何解析？
- 容器统一接口支持异步，直接 `await` 服务方法即可

## 在测试中如何 Mock？
- 使用 `register(..., override=True)` 覆盖已有注册实现
