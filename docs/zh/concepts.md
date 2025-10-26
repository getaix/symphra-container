# 核心概念

## 生命周期（Lifetime）
- `SINGLETON`：全局唯一实例，适合无状态服务或共享资源
- `TRANSIENT`：每次解析新建实例，适合轻量、无资源压力的服务
- `SCOPED`：在作用域内唯一（如一次 Web 请求），适合带上下文的服务
- `FACTORY`：以工厂函数创建实例，灵活控制初始化逻辑

## 服务键（ServiceKey）
- 支持类型键与字符串键混合模式
- 推荐使用类型键，字符串键用于动态或跨模块场景

## 构造函数注入
- 自动分析 `__init__` 参数类型并注入依赖（见 `ConstructorInjector`）
- 支持 `Optional[T]` 与默认值
- 支持 `Injected` 标记进行参数注入标识

## 作用域（Scope）
- 使用 `container.create_scope()` 创建作用域
- 作用域内的 `SCOPED` 服务实例保持唯一
- 作用域结束时负责资源释放

## 拦截器（Interceptor）
- 支持请求前/后/错误拦截，统一记录日志与性能
- 可对解析与生命周期事件进行拦截

## 泛型支持
- 通过 `GenericKey` 区分具体类型参数
- 使用 `register_generic(container, Repository[User], UserRepository)` 注册具体实现

## 循环依赖检测
- 解析时进行循环依赖检测（见 `CircularDependencyDetector`）
- 提供诊断工具与可视化（见 `visualization` 模块）

## 异步支持
- 同步与异步统一解析接口，容器内部在需要时使用 `asyncio` 驱动

## 性能与诊断
- 内置性能指标与计时器，支持诊断报告与依赖图导出
