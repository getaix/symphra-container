# Symphra Container 技术规范文档

## 项目概述

**项目名称**: Symphra Container
**类型**: Python 依赖注入容器库
**目标**: 提供高性能、类型安全、易于使用的 DI 容器，支持多种生命周期、循环依赖处理和框架集成

---

## 设计决策确认表

| 决策项 | 选择方案 | 说明 |
|--------|---------|------|
| **服务键模式** | 混合模式 | 同时支持类型键和字符串键 |
| **字符串键类型提示** | TypedDict + Literal | 通过重载和类型提示保证 IDE 自动补全 |
| **API 风格** | 混合风格 | 同时提供 `resolve()` 和 `get()` 方法 |
| **链式调用** | 不支持 | 每个操作独立，返回 None |
| **生命周期类型** | 4 种 | Singleton, Transient, Scoped, Factory |
| **服务覆盖** | override 参数 | 默认 False（忽略重复），True 时替换 |
| **可选依赖** | 优先容器解析 | 有默认值也优先从容器解析，无则使用默认值 |
| **解析失败** | 抛异常 | 无法解析时立即抛出详细异常 |

---

## 核心 API 快速参考

### 注册 API

```python
# 类型键注册
container.register(UserService)  # 自动装配
container.register(IService, ServiceImpl)  # 指定实现
container.register(Service, lifetime=Lifetime.TRANSIENT)  # 生命周期
container.register(Service, NewImpl, override=True)  # 覆盖

# 字符串键注册
container.register("db", Database)
container.register_factory("logger", create_logger)
container.register_instance("config", config_obj)
container.register_value("api_key", "sk_...")

# 异步工厂
container.register_async_factory("async_db", async_create_db)

# 批量注册
container.scan("myapp.services")  # 自动扫描 @injectable 类
container.register_module(DatabaseModule())  # 模块化注册
```

### 获取 API

```python
# 类型键获取
service: UserService = container.resolve(UserService)  # 推荐
service = container.try_resolve(UserService)  # Optional[UserService]

# 字符串键获取
db: Database = container.get("database")  # 类型注解辅助
db = container.get("database", Database)  # 显式指定类型
db = container.try_get("database")  # Optional[Database]

# 异步获取
service = await container.resolve_async(Service)
service = await container.get_async("service_key")

# 检查和元数据
exists = container.has("database")  # bool
descriptor = container.get_descriptor(UserService)  # 服务描述符
all_loggers = container.get_all(Logger)  # 获取所有同类型服务
```

### 删除和覆盖 API

```python
# 删除
container.unregister(UserService)  # 按类型删除
container.unregister("database")  # 按键删除
container.try_unregister("optional")  # 安全删除
container.unregister(IService, all=True)  # 删除所有实现

# 覆盖
container.replace(OldService, NewService)  # 直接替换
container.unregister(Service)  # 或先删后注册
container.register(Service, NewImpl, override=True)

# 清空
container.clear()  # 清空所有服务
container.clear(lifetime=Lifetime.TRANSIENT)  # 清空特定生命周期
```

### 作用域 API

```python
# 创建作用域
with container.create_scope() as scope:
    service = scope.resolve(UserService)

# 异步作用域
async with container.create_async_scope() as scope:
    service = await scope.resolve_async(UserService)

# 子容器（继承父容器）
child = container.create_child()
```

### 装饰器 API

```python
# 类装饰器
@injectable
class Service: pass  # 默认 Singleton

@injectable.transient
class Service: pass

@injectable.factory
def create_service(): pass

# 方法装饰器
@inject
def process(service: UserService = Injected):
    pass

# 属性注入
class Service:
    db: Database = inject()
    cache: Cache = inject("cache_service")
```

---

## 类型系统架构

### 1. 核心类型层次

```
ServiceKey (Union[Type[T], str])
    ├── Type[T] - 类型键（推荐）
    └── str - 字符串键

Lifetime (Enum)
    ├── SINGLETON - 全局唯一
    ├── TRANSIENT - 每次创建
    ├── SCOPED - 作用域共享
    └── FACTORY - 工厂模式

ProviderType (Enum)
    ├── CLASS - 类构造
    ├── FACTORY - 工厂函数
    ├── INSTANCE - 直接实例
    └── VALUE - 配置值
```

### 2. 类型提示保证

#### 方案 A: 类型键（100% IDE 支持）

```python
class UserService:
    pass

container.register(UserService)
service: UserService = container.resolve(UserService)  # ✅ IDE 完美推断
```

#### 方案 B: 字符串键 + 类型注解

```python
# 使用类型注解作为类型提示来源
db: Database = container.get("database")  # ✅ IDE 从注解推断

# 或显式指定类型
db = container.get("database", Database)  # ✅ IDE 推断为 Database
```

#### 方案 C: Literal + Overload（最优）

```python
from typing_extensions import Literal, overload

class Container:
    @overload
    def get(self, key: Literal["database"]) -> Database: ...

    @overload
    def get(self, key: Literal["cache"]) -> Cache: ...

    @overload
    def get(self, key: str, service_type: Type[T]) -> T: ...

# 使用时 IDE 自动完成
db = container.get("database")  # ✅ IDE 知道返回 Database
cache = container.get("cache")  # ✅ IDE 知道返回 Cache
```

### 3. TypedDict 方案（可选增强）

```python
from typing_extensions import TypedDict

class ServiceRegistry(TypedDict, total=False):
    database: Database
    cache: Cache
    logger: Logger

# 用于 IDE 类型提示和代码生成
registry: ServiceRegistry = {
    "database": PostgresDB(),
    "cache": RedisCache(),
    "logger": FileLogger(),
}

# IDE 可以根据 registry 的定义提供自动补全
```

---

## 循环依赖处理机制

### 问题场景

```python
# 场景 1: 直接循环
class A:
    def __init__(self, b: B):
        self.b = b

class B:
    def __init__(self, a: A):
        self.a = a

# 场景 2: 间接循环
class A:
    def __init__(self, b: B): pass

class B:
    def __init__(self, c: C): pass

class C:
    def __init__(self, a: A): pass
```

### 解决方案

#### 方案 1: Lazy 包装（推荐）✅

```python
from symphra_container import Lazy

class A:
    def __init__(self, b: Lazy[B]):
        self.b = b  # 首次访问 self.b 时才解析 B

class B:
    def __init__(self, a: A):
        self.a = a

# 完全避免循环依赖！
container.register(A)
container.register(B)
a = container.resolve(A)  # ✅ 成功
```

#### 方案 2: 属性/方法注入

```python
class A:
    def __init__(self):
        self.b: Optional[B] = None

class B:
    def __init__(self, a: A):
        self.a = a

# 手动初始化器
def init_a(a: A, b: B):
    a.b = b

container.register(A)
container.register(B)
container.register_initializer(A, init_a, [B])
```

#### 方案 3: 工厂函数延迟

```python
def create_a(b: Lazy[B]):
    return A(b)

container.register_factory(A, create_a)
container.register(B)
```

### 检测机制

```
解析栈: [A]
  ├─ 解析 A 的依赖
  ├─ 需要 B，栈: [A, B]
  │  ├─ 解析 B 的依赖
  │  ├─ 需要 A，栈: [A, B, A]
  │  ├─ 检测到循环！A 已在栈中
  │  └─ 抛出 CircularDependencyError
  │     详细信息: A -> B -> A
```

---

## 生命周期管理详解

### 1. Singleton（单例）

```python
# 全局唯一实例
container.register(Database, lifetime=Lifetime.SINGLETON)

db1 = container.resolve(Database)
db2 = container.resolve(Database)
assert db1 is db2  # ✅ 同一实例

# 子容器也共享
child = container.create_child()
db3 = child.resolve(Database)
assert db3 is db1  # ✅ 全局共享
```

**特性**:
- 线程安全的单例创建（双重检查锁）
- 应用启动时或首次请求时初始化
- 适用于无状态服务（数据库、缓存、日志）

### 2. Transient（瞬态）

```python
# 每次创建新实例
container.register(RequestHandler, lifetime=Lifetime.TRANSIENT)

handler1 = container.resolve(RequestHandler)
handler2 = container.resolve(RequestHandler)
assert handler1 is not handler2  # ✅ 不同实例
```

**特性**:
- 每次请求都创建新实例
- 无内存泄漏风险
- 适用于有状态服务、请求处理器

### 3. Scoped（作用域）

```python
# 作用域内唯一
container.register(UnitOfWork, lifetime=Lifetime.SCOPED)

with container.create_scope() as scope1:
    uow1a = scope1.resolve(UnitOfWork)
    uow1b = scope1.resolve(UnitOfWork)
    assert uow1a is uow1b  # ✅ 作用域内共享

with container.create_scope() as scope2:
    uow2 = scope2.resolve(UnitOfWork)
    assert uow2 is not uow1a  # ✅ 不同作用域隔离
```

**特性**:
- 使用 `contextvars` 实现线程安全
- 作用域销毁时自动清理资源
- 适用于 Web 请求、数据库事务

### 4. Factory（工厂）

```python
# 使用工厂函数创建
def create_db(config: Config):
    return Database(config.db_url)

container.register_factory("database", create_db, lifetime=Lifetime.SINGLETON)

# 工厂可以有依赖，由容器自动注入
db = container.get("database")
```

**特性**:
- 灵活的创建逻辑
- 支持异步工厂
- 可以依赖其他服务

---

## 依赖注入模式

### 1. 构造函数注入（优先）

```python
class UserService:
    def __init__(self, db: Database, logger: Logger):
        self.db = db
        self.logger = logger

# 容器自动注入
service = container.resolve(UserService)
assert service.db is not None
assert service.logger is not None
```

**优势**:
- ✅ 类型安全
- ✅ IDE 支持
- ✅ 不可变对象友好
- ✅ 依赖清晰

### 2. 属性注入（特殊情况）

```python
class Service:
    db: Database = inject()  # 使用描述符
    logger: Logger = inject("logger_service")

# 初始化
service = Service()  # db 和 logger 自动注入
```

**用途**:
- 可选依赖
- 循环依赖
- 遗留代码兼容

### 3. 方法注入（初始化）

```python
class Service:
    def setup(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache

# 注册初始化器
container.register_initializer(
    Service,
    lambda svc, db, cache: svc.setup(db, cache),
    [Database, Cache]
)
```

---

## 错误处理规范

### 异常层次

```
ContainerException (基类)
├── ServiceNotFoundError - 服务未注册
│   └── "Service UserService not found in container"
│
├── CircularDependencyError - 循环依赖
│   └── "Circular dependency detected: A -> B -> C -> A"
│
├── InvalidServiceError - 无效服务定义
│   └── "Service type cannot be None"
│
├── RegistrationError - 注册错误
│   └── "Service UserService already registered, use override=True"
│
└── ResolutionError - 解析错误
    └── "Cannot resolve UserService: missing required dependency 'db'"
```

### 错误消息示例

```python
try:
    container.resolve(NonExistentService)
except ServiceNotFoundError as e:
    # ServiceNotFoundError: Service NonExistentService not found in container
    # Available services:
    #   - UserService (Lifetime.SINGLETON)
    #   - Database (Lifetime.SINGLETON)
    #   - Logger (Lifetime.TRANSIENT)
    pass

try:
    container.resolve(ServiceWithCircularDep)
except CircularDependencyError as e:
    # CircularDependencyError: Circular dependency detected:
    # ServiceA -> ServiceB -> ServiceC -> ServiceA
    #
    # To fix:
    # 1. Use Lazy[ServiceA] in ServiceC
    # 2. Use property injection
    # 3. Restructure your dependencies
    pass
```

---

## 性能目标

| 操作 | 目标 | 说明 |
|-----|------|------|
| **简单解析** | < 1 μs | 单个依赖 |
| **复杂解析** | < 50 μs | 10 层嵌套依赖 |
| **单例缓存** | < 100 ns | 已缓存实例查询 |
| **启动时间** | < 100 ms | 1000 个服务注册 |
| **内存占用** | < 1 MB | 1000 个服务定义 |

---

## 项目结构规划

```
symphra-container/
├── src/symphra_container/
│   ├── __init__.py                 # 公共 API 导出
│   ├── container.py                # 核心容器类
│   ├── registry.py                 # 服务注册表
│   ├── resolver.py                 # 依赖解析器
│   ├── types.py                    # 类型定义
│   ├── enums.py                    # 枚举类型
│   ├── exceptions.py               # 异常定义
│   │
│   ├── lifetimes/
│   │   ├── __init__.py
│   │   ├── manager.py              # 生命周期管理器基类
│   │   ├── singleton.py            # 单例管理器
│   │   ├── transient.py            # 瞬态管理器
│   │   ├── scoped.py               # 作用域管理器
│   │   └── factory.py              # 工厂管理器
│   │
│   ├── injection/
│   │   ├── __init__.py
│   │   ├── detector.py             # 依赖检测器
│   │   ├── constructor.py          # 构造函数注入
│   │   ├── property.py             # 属性注入
│   │   └── method.py               # 方法注入
│   │
│   ├── circular/
│   │   ├── __init__.py
│   │   ├── detector.py             # 循环依赖检测器
│   │   └── lazy_proxy.py           # 延迟代理实现
│   │
│   ├── decorators/
│   │   ├── __init__.py
│   │   ├── injectable.py           # @injectable 装饰器
│   │   └── inject.py               # @inject 装饰器
│   │
│   ├── scopes/
│   │   ├── __init__.py
│   │   ├── scope.py                # 作用域实现
│   │   └── context.py              # 作用域上下文
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── fastapi.py              # FastAPI 集成
│   │   └── flask.py                # Flask 集成
│   │
│   └── utils/
│       ├── __init__.py
│       ├── inspection.py            # 反射工具
│       └── typing_helpers.py        # 类型工具
│
├── tests/
│   ├── unit/
│   │   ├── test_container.py
│   │   ├── test_lifetimes.py
│   │   ├── test_injection.py
│   │   ├── test_circular.py
│   │   └── test_resolver.py
│   │
│   ├── integration/
│   │   ├── test_fastapi.py
│   │   └── test_flask.py
│   │
│   ├── performance/
│   │   └── benchmark.py
│   │
│   └── conftest.py
│
├── docs/
│   ├── index.md
│   ├── guide/
│   │   ├── quick_start.md
│   │   ├── registration.md
│   │   ├── resolution.md
│   │   ├── lifetimes.md
│   │   └── advanced.md
│   │
│   ├── api/
│   │   └── reference.md
│   │
│   └── examples/
│       ├── simple.py
│       ├── fastapi_example.py
│       └── flask_example.py
│
├── pyproject.toml
├── setup.py
├── README.md
├── API_DESIGN.md                   # 完整 API 文档
├── TECHNICAL_SPEC.md               # 本文件
└── CHANGELOG.md
```

---

## 开发阶段分解

### 阶段 1: 核心架构（3-5 天）
- [ ] 项目初始化和工程配置
- [ ] 核心类型系统设计
- [ ] 容器基础类实现
- [ ] 依赖解析器基础实现

### 阶段 2: 注册与解析（4-6 天）
- [ ] 多种生命周期管理器
- [ ] 工厂函数和实例注册
- [ ] 自动装配功能
- [ ] 属性和方法注入

### 阶段 3: 高级特性（5-7 天）
- [ ] 循环依赖检测
- [ ] Lazy Proxy 实现
- [ ] 作用域管理
- [ ] 异步支持

### 阶段 4: 框架集成（4-5 天）
- [ ] 装饰器系统
- [ ] FastAPI 集成
- [ ] Flask 集成
- [ ] 配置加载器

### 阶段 5: 测试与优化（5-7 天）
- [ ] 单元测试和集成测试
- [ ] 性能基准测试和优化
- [ ] 类型检查完善
- [ ] 文档编写

---

## 关键设计原则

### 1. KISS（保持简单）
- 简洁的 API 设计
- 最小化用户配置
- 清晰的错误消息

### 2. SOLID 原则
- **S**: 单一职责 - 每个类只负责一个方面
- **O**: 开闭原则 - 易于扩展，难以修改
- **L**: Liskov 替换 - 遵循协议定义
- **I**: 接口隔离 - 精细化接口
- **D**: 依赖倒置 - 依赖抽象，不依赖具体

### 3. 类型安全
- 完整的类型提示
- MyPy 严格模式通过
- IDE 自动补全支持

### 4. 高性能
- 解析栈缓存
- 单例快速查询
- 最小化反射调用

---

## 检验清单

完成后需验证：

- [ ] 所有 4 种生命周期正确实现
- [ ] 字符串键和类型键混合使用
- [ ] IDE 自动补全正常工作
- [ ] 循环依赖自动检测
- [ ] Lazy Proxy 正确工作
- [ ] 异步容器完全支持
- [ ] FastAPI/Flask 集成可用
- [ ] 测试覆盖率 ≥ 90%
- [ ] 文档完整详细
- [ ] 性能指标达标
