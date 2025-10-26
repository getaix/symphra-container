# Symphra Container 完整 API 设计文档

## 1. 类型系统设计

### 1.1 核心类型定义

```python
# src/symphra_container/types.py

from typing import TypeVar, Generic, Protocol, Union, Optional, Callable, Any, Dict, Type
from typing_extensions import TypedDict, Literal, overload
from enum import Enum

# ============ 基础类型 ============

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
ServiceKey = Union[Type[T], str]

class Lifetime(str, Enum):
    """服务生命周期枚举"""
    SINGLETON = "singleton"      # 全局唯一
    TRANSIENT = "transient"      # 每次创建新实例
    SCOPED = "scoped"            # 作用域内共享
    FACTORY = "factory"          # 工厂模式

class ProviderType(str, Enum):
    """提供者类型"""
    CLASS = "class"              # 类构造函数
    FACTORY = "factory"          # 工厂函数
    INSTANCE = "instance"        # 直接实例
    VALUE = "value"              # 配置值

# ============ 服务描述符 ============

class ServiceDescriptor(Generic[T]):
    """服务描述符 - 存储服务的完整注册信息"""
    service_type: Type[T] | str
    impl_type: Optional[Type[T]]
    factory: Optional[Callable[..., T]]
    instance: Optional[T]
    lifetime: Lifetime
    provider_type: ProviderType
    is_singleton: bool
    metadata: Dict[str, Any]

# ============ 错误类型 ============

class ServiceNotFoundError(Exception):
    """服务未找到异常"""
    pass

class CircularDependencyError(Exception):
    """循环依赖异常"""
    pass

class InvalidServiceError(Exception):
    """无效的服务定义"""
    pass

class RegistrationError(Exception):
    """注册错误"""
    pass

# ============ 协议定义 ============

class Provider(Protocol[T_co]):
    """服务提供者协议"""
    def provide(self) -> T_co: ...

class Resolver(Protocol):
    """依赖解析器协议"""
    def resolve(self, service_type: Type[T], container: "Container") -> T: ...

class LifetimeManager(Protocol):
    """生命周期管理器协议"""
    def get_instance(self, factory: Callable) -> Any: ...
    def dispose(self) -> None: ...
```

### 1.2 字符串键类型提示方案

```python
# src/symphra_container/registry.py

from typing_extensions import TypedDict, Literal, overload

class ServiceRegistry(TypedDict, total=False):
    """
    服务注册表类型定义 - 用于IDE类型提示

    使用方式:
    registry: ServiceRegistry = {
        "database": DatabaseImpl(),
        "cache": CacheImpl(),
        "logger": LoggerImpl(),
    }

    # IDE 会推断 registry["database"] 的类型
    """
    # 基础服务
    database: Any
    cache: Any
    logger: Any
    config: Any
    # ... 更多服务定义

    # 这样定义后，使用字符串键时 IDE 能提供自动补全

# ============ 更优雅的方案：使用 Literal + overload ============

@overload
def get(self, key: Literal["database"]) -> Database: ...

@overload
def get(self, key: Literal["cache"]) -> Cache: ...

@overload
def get(self, key: Literal["logger"]) -> Logger: ...

@overload
def get(self, key: str, service_type: Type[T]) -> T: ...

def get(self, key: str, service_type: Type[T] | None = None) -> T:
    """获取服务"""
    ...

# 使用示例
db = container.get("database")  # IDE 推断为 Database 类型
cache = container.get("cache")  # IDE 推断为 Cache 类型
logger = container.get("logger")  # IDE 推断为 Logger 类型

# 未知服务时需指定类型
service = container.get("custom_service", CustomService)
```

---

## 2. 完整 API 设计

### 2.1 容器初始化

```python
from symphra_container import Container, Lifetime, inject

# ============ 初始化容器 ============

# 方式 1: 创建新容器
container = Container()

# 方式 2: 创建子容器（继承父容器配置）
child_container = container.create_child()

# 方式 3: 创建带名称的容器（便于调试）
container = Container(name="MyApp")

# 方式 4: 从配置文件创建
container = Container.from_config("config.yaml")
```

### 2.2 注册服务

#### 2.2.1 基础注册（类型键）

```python
# ============ 类型键注册 ============

# 注册 1: 自动装配（使用实现类本身）
container.register(UserService)
# 等价于: container.register(UserService, UserService)

# 注册 2: 指定实现类
class IUserService(Protocol):
    def get_user(self, id: int) -> User: ...

container.register(IUserService, UserService)

# 注册 3: 指定生命周期（默认 SINGLETON）
container.register(
    UserService,
    lifetime=Lifetime.TRANSIENT
)

# 注册 4: 带覆盖参数
container.register(
    IUserService,
    UserServiceV1,
    lifetime=Lifetime.SINGLETON,
    override=False  # 默认 False，忽略重复注册
)

# 更新为 V2（使用 override=True）
container.register(
    IUserService,
    UserServiceV2,
    override=True  # 覆盖之前的注册
)

# ============ 类型键获取 ============

# 获取 1: 基础解析
user_service = container.resolve(UserService)  # 返回 UserService 实例

# 获取 2: 解析接口（自动推断为实现类）
service = container.resolve(IUserService)  # 返回 UserService 实例

# 获取 3: 尝试解析（返回 Optional）
service = container.try_resolve(NonExistentService)  # 返回 None
```

#### 2.2.2 字符串键注册

```python
# ============ 字符串键注册 ============

# 注册 1: 类实现
container.register(
    "user_service",
    UserService,
    lifetime=Lifetime.SINGLETON
)

# 注册 2: 工厂函数
def create_database():
    return Database(
        host="localhost",
        port=5432
    )

container.register_factory(
    "database",
    create_database,
    lifetime=Lifetime.SINGLETON
)

# 注册 3: 直接实例
config = Config.from_file("config.yaml")
container.register_instance("config", config)

# 注册 4: 配置值
container.register_value("api_key", "sk_live_xxxxx")
container.register_value("max_connections", 100)
container.register_value("debug_mode", True)

# ============ 字符串键获取 ============

# 获取 1: 基础获取（需要类型注解辅助）
db: Database = container.get("database")  # IDE 推断为 Database

# 获取 2: 显式指定类型
db = container.get("database", Database)

# 获取 3: 获取配置值
api_key = container.get("api_key")  # 返回 str
max_conn = container.get("max_connections")  # 返回 int

# 获取 4: 尝试获取
db = container.try_get("optional_service")  # 返回 None if not found
```

#### 2.2.3 工厂函数注册

```python
# ============ 工厂函数（同步） ============

# 方式 1: 简单工厂
def create_logger():
    return Logger("myapp.log")

container.register_factory(
    "logger",
    create_logger,
    lifetime=Lifetime.SINGLETON
)

# 方式 2: 工厂依赖容器
def create_db_connection(container: Container):
    config = container.resolve(Config)
    return Database(**config.database)

container.register_factory(
    "db_conn",
    create_db_connection,
    lifetime=Lifetime.SINGLETON
)

# 方式 3: 工厂依赖其他服务
def create_user_service(db: Database, logger: Logger):
    return UserService(db, logger)

# 容器会自动解析 db 和 logger 参数
container.register_factory(
    "user_service",
    create_user_service,
    lifetime=Lifetime.TRANSIENT
)

# ============ 工厂函数（异步） ============

async def create_async_db():
    return await Database.connect("postgresql://...")

container.register_async_factory(
    "async_db",
    create_async_db,
    lifetime=Lifetime.SINGLETON
)

# 异步解析
db = await container.resolve_async("async_db")
```

#### 2.2.4 高级注册模式

```python
# ============ 条件注册 ============

# 根据配置条件注册
if config.use_postgres:
    container.register(IDatabase, PostgresDatabase)
else:
    container.register(IDatabase, SQLiteDatabase)

# ============ 批量注册 ============

# 同时注册多个实现为同一接口
implementations = [
    UserServiceImpl,
    OrderServiceImpl,
    PaymentServiceImpl,
]

for impl in implementations:
    # 使用模块名 + 类名作为 key
    key = f"{impl.__module__}.{impl.__name__}"
    container.register(key, impl)

# ============ 装饰器注册（自动扫描）============

@injectable(lifetime=Lifetime.SINGLETON)
class UserRepository:
    pass

@injectable.transient
class OrderService:
    pass

@injectable.factory
def create_cache():
    return Redis()

# 自动注册所有标记的类
container.scan("myapp.services")

# ============ 模块化注册 ============

class DatabaseModule(ContainerModule):
    def configure(self, container: Container):
        container.register("db", DatabaseImpl)
        container.register("connection_pool", ConnectionPool)

container.register_module(DatabaseModule())
```

### 2.3 获取服务

```python
# ============ 类型键获取 ============

# 基础解析 - 推荐用于有类型的情况
service: UserService = container.resolve(UserService)

# 解析接口
service: IUserService = container.resolve(IUserService)

# 尝试解析 - 返回 Optional
service = container.try_resolve(UserService)  # Optional[UserService]

# ============ 字符串键获取 ============

# 方式 1: 带类型注解（推荐）
db: Database = container.get("database")

# 方式 2: 显式指定类型
db = container.get("database", Database)

# 方式 3: 尝试获取
db = container.try_get("database")  # Optional[Database]

# 方式 4: 获取所有注册的某类型服务
loggers = container.get_all(Logger)  # List[Logger]
loggers = container.get_all("logger*")  # 使用 glob 模式匹配

# ============ 获取服务信息 ============

# 检查服务是否已注册
exists = container.has("database")  # bool
exists = container.has(UserService)  # bool

# 获取服务元数据
descriptor = container.get_descriptor(UserService)
print(descriptor.lifetime)  # Lifetime.SINGLETON
print(descriptor.lifetime_manager)  # SingletonManager instance

# ============ 异步获取 ============

# 异步解析服务
db = await container.resolve_async(Database)

# 异步获取字符串键
service = await container.get_async("async_service")
```

### 2.4 删除和覆盖

```python
# ============ 删除服务 ============

# 删除 1: 按类型删除
container.unregister(UserService)

# 删除 2: 按字符串键删除
container.unregister("database")

# 删除 3: 删除所有实现某接口的服务
container.unregister(IUserService, all=True)

# 删除 4: 安全删除（不存在也不报错）
container.try_unregister("optional_service")

# ============ 清空容器 ============

# 清空所有服务（谨慎使用）
container.clear()

# 清空特定生命周期的服务
container.clear(lifetime=Lifetime.TRANSIENT)

# ============ 覆盖服务 ============

# 方式 1: 使用 override 参数（注册时）
container.register(UserService, NewUserService, override=True)

# 方式 2: 先删除后注册
container.unregister(UserService)
container.register(UserService, NewUserService)

# 方式 3: 直接替换（新增方法）
container.replace(UserService, NewUserService)
```

### 2.5 作用域管理

```python
# ============ 创建作用域 ============

# 方式 1: Context Manager（推荐）
with container.create_scope() as scope:
    service = scope.resolve(UserService)
    # 在作用域内，Scoped 生命周期的服务共享实例
    # 作用域结束时自动清理资源

# 方式 2: 手动管理
scope = container.create_scope()
try:
    service = scope.resolve(UserService)
finally:
    scope.dispose()

# ============ 异步作用域 ============

async with container.create_async_scope() as scope:
    service = await scope.resolve_async(UserService)

# ============ 作用域特性 ============

# 继承父容器的 Singleton 和 Transient
# 为 Scoped 生命周期的服务提供隔离环境

with container.create_scope() as scope1:
    user_service1 = scope1.resolve(UserService)  # Scoped

with container.create_scope() as scope2:
    user_service2 = scope2.resolve(UserService)  # 不同实例

# Singleton 在全局共享
db = container.resolve(Database)  # 全局单例
```

### 2.6 依赖注入（构造函数）

```python
# ============ 自动装配（构造函数） ============

class UserRepository:
    def __init__(self, db: Database):  # 类型注解
        self.db = db

class UserService:
    def __init__(self, repo: UserRepository, logger: Logger):
        self.repo = repo
        self.logger = logger

# 注册
container.register(Database, PostgresDatabase)
container.register(UserRepository)
container.register(UserService)

# 自动解析完整依赖链
service = container.resolve(UserService)
# 容器自动解析：UserService -> UserRepository -> Database

# ============ 可选依赖（有默认值） ============

class ConfigService:
    def __init__(
        self,
        db: Database,  # 必须从容器解析
        timeout: int = 30,  # 优先容器解析，无则用默认值
        max_retries: int = 3
    ):
        self.db = db
        self.timeout = timeout
        self.max_retries = max_retries

# 使用方式
container.register(Database, PostgresDatabase)
container.register("timeout", 60)  # 可选：覆盖默认值

service = container.resolve(ConfigService)
# service.db -> Database 实例
# service.timeout -> 60（来自容器）或 30（默认值）
# service.max_retries -> 3（默认值，容器无此注册）

# ============ 循环依赖处理 ============

class UserService:
    def __init__(self, order_service: "OrderService"):  # 前向引用
        self.order_service = order_service

class OrderService:
    def __init__(self, user_service: UserService):  # 循环依赖！
        self.user_service = user_service

# 方式 1: 使用 Lazy 包装（推荐）
from symphra_container import Lazy

class UserService:
    def __init__(self, order_service: Lazy[OrderService]):  # 延迟注入
        self.order_service = order_service  # 首次访问时才解析

class OrderService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

container.register(UserService)
container.register(OrderService)
service = container.resolve(UserService)  # 成功！

# 方式 2: 属性注入
class UserService:
    def __init__(self):
        self.order_service: Optional[OrderService] = None

    def set_order_service(self, os: OrderService):
        self.order_service = os

container.register(UserService)
container.register(OrderService)
container.register_initializer(UserService, lambda us, os: us.set_order_service(os), [OrderService])
```

### 2.7 装饰器使用

```python
from symphra_container import inject, injectable, Injected, Lazy

# ============ 类装饰器 ============

@injectable
class UserService:
    """默认 Lifetime.SINGLETON"""
    pass

@injectable(lifetime=Lifetime.TRANSIENT)
class RequestHandler:
    pass

@injectable.singleton
class Cache:
    pass

@injectable.transient
class Logger:
    pass

@injectable.scoped
class UnitOfWork:
    pass

@injectable.factory
def create_config():
    return Config.load()

# 自动注册到默认容器
# container.scan("myapp.services")

# ============ 方法/函数装饰器 ============

# 方式 1: 参数标记
@inject
def process_order(
    order: Order,
    payment_service: PaymentService = Injected,  # 从容器注入
    notification: NotificationService = Injected
):
    return payment_service.process(order)

# 调用时
order = Order(id=1)
result = process_order(order)  # 自动注入其他参数

# 方式 2: 显式参数名
@inject({"payment_service": PaymentService})
def process_order(order, payment_service):
    return payment_service.process(order)

# 方式 3: 使用容器实例
@inject(container=my_container)
def setup_database(db: Database = Injected):
    db.init()

# ============ 属性注入 ============

from typing import ClassVar

class UserService:
    container: ClassVar[Container]

    db: Database = inject()  # 使用描述符注入
    cache: Cache = inject("cache_service")  # 注入指定名称服务

    def __init__(self):
        pass  # db 和 cache 会自动注入

# 需要配置容器
UserService.container = container
```

### 2.8 FastAPI 集成

```python
from symphra_container.integrations.fastapi import DIMiddleware, inject_dependencies

# ============ 中间件方式 ============

from fastapi import FastAPI

app = FastAPI()
container = Container()

# 注册服务
container.register(UserService)
container.register(Database)

# 添加 DI 中间件
app.add_middleware(DIMiddleware, container=container)

# 路由自动注入
@app.get("/users/{user_id}")
def get_user(
    user_id: int,
    user_service: UserService = Injected  # 自动从容器注入
):
    return user_service.get_user(user_id)

# ============ 装饰器方式 ============

@app.get("/orders/{order_id}")
@inject_dependencies(container)
def get_order(
    order_id: int,
    order_service: OrderService = Injected,
    logger: Logger = Injected
):
    logger.info(f"Getting order {order_id}")
    return order_service.get_order(order_id)

# ============ 异步支持 ============

@app.get("/async-users/{user_id}")
async def get_async_user(
    user_id: int,
    user_service: UserService = Injected
):
    return await user_service.get_user_async(user_id)

# ============ 请求作用域 ============

class RequestService:
    """每个请求创建一个实例"""
    def __init__(self):
        self.id = uuid4()

container.register(
    RequestService,
    lifetime=Lifetime.SCOPED
)

@app.get("/request-info")
def get_request_info(service: RequestService = Injected):
    return {"request_id": str(service.id)}

# 每个请求的 service.id 都不同
```

### 2.9 Flask 集成

```python
from symphra_container.integrations.flask import FlaskContainer

# ============ Flask 扩展方式 ============

from flask import Flask

app = Flask(__name__)
container = FlaskContainer(app)

# 注册服务
container.register(UserService)
container.register(Database)

@app.route("/users/<user_id>")
@container.inject
def get_user(user_id, user_service: UserService = Injected):
    return user_service.get_user(user_id)

# ============ 应用上下文集成 ============

# 自动创建请求作用域
with app.app_context():
    service = container.resolve(RequestService)  # Scoped 实例

with app.test_request_context():
    service = container.resolve(RequestService)  # 新的 Scoped 实例
```

---

## 3. 完整使用示例

### 3.1 简单应用

```python
from symphra_container import Container, Lifetime

# 初始化容器
container = Container()

# 定义服务
class Database:
    def __init__(self):
        print("Database initialized")

class UserRepository:
    def __init__(self, db: Database):
        self.db = db

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, id: int):
        return f"User {id}"

# 注册服务
container.register(Database, lifetime=Lifetime.SINGLETON)
container.register(UserRepository)
container.register(UserService)

# 使用
service = container.resolve(UserService)
user = service.get_user(1)
print(user)  # User 1
```

### 3.2 复杂应用

```python
from symphra_container import Container, Lifetime, inject, injectable

# 装饰器注册
@injectable.singleton
class Config:
    def __init__(self):
        self.debug = True
        self.db_url = "postgresql://..."

@injectable.singleton
class Database:
    def __init__(self, config: Config):
        self.config = config

@injectable
class Cache:
    pass

@injectable.transient
class RequestContext:
    def __init__(self, cache: Cache):
        self.cache = cache

@injectable.factory
def create_logger(config: Config):
    import logging
    return logging.getLogger("app")

# 容器配置
container = Container()
container.scan("myapp")  # 自动扫描并注册

# 使用
with container.create_scope() as scope:
    db = scope.resolve(Database)
    ctx = scope.resolve(RequestContext)
    logger = scope.resolve(Logger)

    # 在作用域内工作
    ...
```

### 3.3 字符串键混合使用

```python
from symphra_container import Container

container = Container()

# 类型键注册
container.register(UserService)
container.register(Database)

# 字符串键注册
container.register("api_key", "sk_live_xxxxx")
container.register("max_connections", 100)
container.register_instance("config", load_config())

# 类型键解析
user_service = container.resolve(UserService)

# 字符串键解析
api_key: str = container.get("api_key")
max_conn: int = container.get("max_connections")
config: Config = container.get("config")

# 混合使用
class PaymentService:
    def __init__(self, api_key: str):
        self.api_key = api_key

def create_payment_service(container: Container):
    api_key = container.get("api_key")
    return PaymentService(api_key)

container.register_factory(PaymentService, create_payment_service)
```

---

## 4. 类型提示完整对应表

| 注册方式 | 获取方式 | 类型提示 | IDE 自动补全 |
|---------|---------|---------|------------|
| `register(UserService)` | `resolve(UserService)` | ✅ 完美 | ✅ 完美 |
| `register(IService, Impl)` | `resolve(IService)` | ✅ 完美 | ✅ 完美 |
| `register("db", Database)` | `get("db", Database)` | ✅ 完美 | ✅ 可以 |
| `register("db", Database)` | `db: Database = get("db")` | ✅ 完美 | ✅ 可以 |
| `register_factory("logger", fn)` | `get("logger", Logger)` | ✅ 完美 | ✅ 可以 |
| `@injectable class Service` | `resolve(Service)` | ✅ 完美 | ✅ 完美 |
| `@inject decorator` | 自动注入参数 | ✅ 完美 | ✅ 完美 |

---

## 5. 错误处理

```python
from symphra_container import (
    Container,
    ServiceNotFoundError,
    CircularDependencyError,
    InvalidServiceError,
    RegistrationError
)

try:
    # 服务未注册
    service = container.resolve(NonExistentService)
except ServiceNotFoundError as e:
    print(f"Error: {e}")  # Service NonExistentService not found

try:
    # 循环依赖
    service = container.resolve(CircularServiceA)
except CircularDependencyError as e:
    print(f"Error: {e}")  # Circular dependency detected: A -> B -> A

try:
    # 无效注册
    container.register(None, "invalid")
except InvalidServiceError as e:
    print(f"Error: {e}")

try:
    # 重复注册（override=False）
    container.register(Service, impl1)
    container.register(Service, impl2)  # override=False (default)
except RegistrationError as e:
    print(f"Error: {e}")  # Service already registered, use override=True
```

---

## 6. API 总结速查表

### 注册相关
- `register(service_type, impl=None, lifetime=SINGLETON, override=False)` - 基础注册
- `register_factory(name, factory, lifetime=SINGLETON)` - 工厂注册
- `register_instance(name, instance)` - 实例注册
- `register_value(name, value)` - 值注册
- `register_async_factory(name, async_factory)` - 异步工厂
- `register_module(module)` - 模块注册
- `scan(package)` - 自动扫描注册

### 获取相关
- `resolve(service_type)` - 解析类型
- `resolve_async(service_type)` - 异步解析
- `get(key, service_type=None)` - 获取（支持字符串和类型键）
- `get_async(key)` - 异步获取
- `try_resolve(service_type)` - 尝试解析，返回 Optional
- `try_get(key)` - 尝试获取
- `get_all(service_type or pattern)` - 获取所有

### 检查相关
- `has(key)` - 检查服务是否存在
- `get_descriptor(key)` - 获取服务描述符

### 删除相关
- `unregister(key, all=False)` - 删除服务
- `try_unregister(key)` - 尝试删除
- `clear(lifetime=None)` - 清空容器
- `replace(old_key, new_impl)` - 替换服务

### 作用域相关
- `create_scope()` - 创建作用域
- `create_child()` - 创建子容器
- `create_async_scope()` - 创建异步作用域

### 装饰器相关
- `@injectable` - 标记可注入类
- `@injectable.singleton` - 单例标记
- `@injectable.transient` - 瞬态标记
- `@injectable.scoped` - 作用域标记
- `@inject` - 方法注入装饰器
- `Injected` - 参数注入标记
- `Lazy[T]` - 延迟注入包装
