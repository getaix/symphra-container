"""核心类型定义模块.

定义了容器系统中使用的所有类型和泛型约束条件.
包含:
  - 生命周期类型枚举
  - 服务键类型定义
  - 注入点类型定义
  - 工厂函数类型定义
  - 拦截器类型定义
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
from typing import (
    Any,
    Protocol,
    TypeVar,
)

# ===================== 泛型类型变量 =====================

# 表示服务类型(协变, 用于 Protocol)
T_co = TypeVar("T_co", covariant=True)
# 表示服务实现类型(可能与接口不同)
S = TypeVar("S", bound=Any)
# 表示工厂返回类型
R = TypeVar("R")
# 通用类型变量
T = TypeVar("T")

# ===================== 生命周期枚举 =====================


class Lifetime(Enum):
    """服务生命周期类型枚举.

    定义了服务实例在容器中的生命周期管理策略:

    Attributes:
        SINGLETON: 全局单例,容器中只有一个实例
        TRANSIENT: 瞬时模式,每次解析都创建新实例
        SCOPED: 作用域模式,同一作用域内共享实例
        FACTORY: 工厂模式,使用工厂函数创建实例

    Examples:
        >>> container.register(UserService, lifetime=Lifetime.SINGLETON)
        >>> service1 = container.resolve(UserService)
        >>> service2 = container.resolve(UserService)
        >>> assert service1 is service2  # 同一实例
    """

    # 单例生命周期 - 全局唯一
    SINGLETON = auto()

    # 瞬时生命周期 - 每次新建
    TRANSIENT = auto()

    # 作用域生命周期 - 作用域内共享
    SCOPED = auto()

    # 工厂生命周期 - 工厂函数创建
    FACTORY = auto()


# ===================== 服务键类型定义 =====================

# 服务键可以是类型或字符串
ServiceKey = type | str

# 注册时的键类型(支持类型,字符串或 None)
RegistrationKey = type | str | None


# ===================== 工厂函数类型定义 =====================


class SyncFactory(Protocol[T_co]):
    """同步工厂函数协议.

    定义了同步工厂函数的调用签名.

    Args:
        *args: 由容器注入的位置参数
        **kwargs: 由容器注入的关键字参数

    Returns:
        返回服务实例 T_co

    Examples:
        >>> def create_user_service(db: Database) -> UserService:
        ...     return UserService(db)
        >>> container.register_factory(
        ...     UserService,
        ...     create_user_service,
        ...     lifetime=Lifetime.SINGLETON
        ... )
    """

    def __call__(self, *args: Any, **kwargs: Any) -> T_co:
        """执行工厂函数创建实例."""
        ...


class AsyncFactory(Protocol[T_co]):
    """异步工厂函数协议.

    定义了异步工厂函数的调用签名.异步工厂函数在 AsyncContainer 中使用.

    Args:
        *args: 由容器注入的位置参数
        **kwargs: 由容器注入的关键字参数

    Returns:
        返回可等待的服务实例 T_co

    Examples:
        >>> async def create_db_service() -> Database:
        ...     db = Database()
        ...     await db.connect()
        ...     return db
        >>> container.register_async_factory(
        ...     Database,
        ...     create_db_service,
        ...     lifetime=Lifetime.SINGLETON
        ... )
    """

    async def __call__(self, *args: Any, **kwargs: Any) -> T_co:
        """执行异步工厂函数创建实例."""
        ...


# ===================== 拦截器类型定义 =====================


class InterceptorContext(Protocol):
    """拦截器上下文协议.

    定义了拦截器在执行时获得的上下文信息.

    Attributes:
        service_key: 被解析的服务键
        service_type: 服务的类型
        lifetime: 服务的生命周期
        args: 传入的位置参数
        kwargs: 传入的关键字参数
        instance: 创建的实例(仅在 after 阶段可用)
    """

    @property
    def service_key(self) -> ServiceKey:
        """获取服务键."""
        ...

    @property
    def service_type(self) -> type:
        """获取服务类型."""
        ...

    @property
    def lifetime(self) -> Lifetime:
        """获取生命周期."""
        ...

    @property
    def args(self) -> tuple[Any, ...]:
        """获取位置参数."""
        ...

    @property
    def kwargs(self) -> dict[str, Any]:
        """获取关键字参数."""
        ...

    @property
    def instance(self) -> Any | None:
        """获取创建的实例(仅在 after 阶段)."""
        ...


class BeforeInterceptor(Protocol):
    """前置拦截器协议.

    在服务解析前执行,可用于:
    - 验证服务键和参数
    - 日志记录
    - 性能监测开始

    Args:
        context: 拦截器上下文

    Returns:
        应返回 True 继续解析,False 则中止

    Examples:
        >>> def log_before_resolution(context: InterceptorContext) -> bool:
        ...     print(f"解析服务: {context.service_key}")
        ...     return True
        >>> container.add_interceptor("before", log_before_resolution)
    """

    def __call__(self, context: InterceptorContext) -> bool:
        """在解析前执行."""
        ...


class AfterInterceptor(Protocol):
    """后置拦截器协议.

    在服务解析后执行,可用于:
    - 初始化或配置实例
    - 性能监测结束
    - 注册回调函数

    Args:
        context: 拦截器上下文
        instance: 创建的服务实例

    Returns:
        可返回修改后的实例,或 None 保持原实例

    Examples:
        >>> def log_after_resolution(context, instance):
        ...     print(f"解析完成: {context.service_key}")
        ...     return instance
        >>> container.add_interceptor("after", log_after_resolution)
    """

    def __call__(self, context: InterceptorContext, instance: Any) -> Any | None:
        """在解析后执行."""
        ...


class ErrorInterceptor(Protocol):
    """错误拦截器协议.

    在解析过程中出现错误时执行,可用于:
    - 错误日志记录
    - 错误恢复逻辑
    - 链式处理

    Args:
        context: 拦截器上下文
        exception: 发生的异常

    Returns:
        应返回 None(忽略错误)或抛出异常

    Examples:
        >>> def handle_resolution_error(context, exception):
        ...     print(f"解析失败: {context.service_key}, 错误: {exception}")
        ...     raise exception
        >>> container.add_interceptor("error", handle_resolution_error)
    """

    def __call__(self, context: InterceptorContext, exception: Exception) -> None:
        """在解析出错时执行."""
        ...


# ===================== 依赖描述符类型 =====================


class DependencyDescriptor(Protocol):
    """依赖描述符协议.

    描述一个依赖项,包含其类型,名称和可选状态等信息.
    """

    @property
    def key(self) -> ServiceKey:
        """获取服务键."""
        ...

    @property
    def service_type(self) -> type:
        """获取服务类型."""
        ...

    @property
    def is_optional(self) -> bool:
        """依赖是否可选."""
        ...

    @property
    def default_value(self) -> Any:
        """获取默认值."""
        ...


# ===================== 作用域相关类型 =====================


class Scope(Protocol):
    """作用域协议.

    定义了作用域的基本操作,用于管理 SCOPED 生命周期的实例.

    Methods:
        __enter__: 进入作用域
        __exit__: 离开作用域
        get_instance: 获取作用域内的实例
        set_instance: 设置作用域内的实例
    """

    def __enter__(self) -> Scope:
        """进入作用域."""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """离开作用域."""
        ...

    def get_instance(self, key: ServiceKey) -> Any | None:
        """获取作用域内的实例缓存."""
        ...

    def set_instance(self, key: ServiceKey, instance: Any) -> None:
        """设置作用域内的实例缓存."""
        ...

    def dispose(self) -> None:
        """释放作用域内的所有资源."""
        ...


# ===================== 可释放接口类型 =====================


class Disposable(Protocol):
    """可释放接口协议.

    定义了支持资源释放的对象的接口.

    Methods:
        dispose: 释放资源
        dispose_async: 异步释放资源
    """

    def dispose(self) -> None:
        """同步释放资源."""
        ...


class AsyncDisposable(Protocol):
    """异步可释放接口协议."""

    async def dispose_async(self) -> None:
        """异步释放资源."""
        ...


# ===================== 容器配置类型 =====================


class ContainerConfig(Protocol):
    """容器配置协议.

    定义了容器的配置参数.

    Attributes:
        enable_auto_wiring: 是否启用自动装配
        enable_lazy_loading: 是否启用懒加载
        strict_mode: 是否启用严格模式
    """

    enable_auto_wiring: bool
    enable_lazy_loading: bool
    strict_mode: bool


# ===================== 注入标记类型 =====================


class InjectionMarker:
    """注入标记类.

    用于标记函数参数应该被容器注入.

    Examples:
        >>> from symphra_container import Container, Injected
        >>> container = Container()
        >>> def my_function(service: UserService = Injected):
        ...     # service 会被容器自动注入
        ...     pass
    """

    def __init__(self) -> None:
        """初始化注入标记."""

    def __repr__(self) -> str:
        """返回字符串表示."""
        return "Injected"


# 全局注入标记实例
Injected = InjectionMarker()

# ===================== 类型别名 =====================

# 服务创建器类型(支持同步和异步工厂)
ServiceCreator = Callable[..., T] | Callable[..., Any]

# 拦截器回调类型
InterceptorCallback = BeforeInterceptor | AfterInterceptor | ErrorInterceptor

# 拦截器字典类型
InterceptorDict = dict[str, list[InterceptorCallback]]
