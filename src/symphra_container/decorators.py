"""装饰器系统模块.

提供用于标记和配置服务的装饰器,简化依赖注入容器的使用.

主要装饰器:
  - injectable: 标记类为可注入服务
  - singleton: 标记服务为单例
  - transient: 标记服务为瞬时
  - scoped: 标记服务为作用域服务
  - factory: 标记函数为工厂
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, TypeVar

from .types import Lifetime

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class ServiceMetadata:
    """服务元数据.

    存储通过装饰器附加到类或函数的元数据.

    Attributes:
        service_type: 服务类型(可以是类或函数)
        lifetime: 生命周期
        key: 服务键(可选)
    """

    def __init__(
        self,
        service_type: type | Callable[..., Any],
        lifetime: Lifetime = Lifetime.TRANSIENT,
        key: Any | None = None,
    ) -> None:
        """初始化服务元数据.

        Args:
            service_type: 服务类型(可以是类或函数)
            lifetime: 生命周期
            key: 服务键
        """
        self.service_type = service_type
        self.lifetime = lifetime
        self.key = key


def injectable(
    cls_or_lifetime: type | Lifetime = Lifetime.TRANSIENT,
    *,
    key: Any | None = None,
) -> Callable[[type], type] | type:
    """标记类为可注入服务.

    使用此装饰器标记一个类,使其可以被容器自动发现和注册.

    Args:
        cls_or_lifetime: 类或生命周期(作为位置参数)
        key: 服务键(作为关键字参数)

    Returns:
        装饰后的类

    Examples:
        >>> @injectable
        ... class UserService:
        ...     pass
        >>>
        >>> @injectable(Lifetime.SINGLETON)
        ... class DatabaseService:
        ...     pass
        >>>
        >>> @injectable(key="custom_key")
        ... class CustomService:
        ...     pass
    """
    # 处理 @injectable 无参数的情况
    if isinstance(cls_or_lifetime, type):
        cls = cls_or_lifetime
        lifetime = Lifetime.TRANSIENT
        return _apply_injectable_decorator(cls, lifetime, key)

    # 处理 @injectable() 或 @injectable(Lifetime.SINGLETON) 的情况
    lifetime = cls_or_lifetime if isinstance(cls_or_lifetime, Lifetime) else Lifetime.TRANSIENT

    def decorator(cls: type) -> type:
        return _apply_injectable_decorator(cls, lifetime, key)

    return decorator


def _apply_injectable_decorator(
    cls: type,
    lifetime: Lifetime,
    key: Any | None,
) -> type:
    """应用 injectable 装饰器到类.

    Args:
        cls: 要装饰的类
        lifetime: 生命周期
        key: 服务键

    Returns:
        装饰后的类
    """
    service_key = key or cls
    metadata = ServiceMetadata(
        service_type=cls,
        lifetime=lifetime,
        key=service_key,
    )
    cls.__symphra_metadata__ = metadata  # type: ignore
    return cls


def singleton(cls: type) -> type:
    """标记类为单例服务.

    等同于 @injectable(Lifetime.SINGLETON).

    Args:
        cls: 要装饰的类

    Returns:
        装饰后的类

    Examples:
        >>> @singleton
        ... class DatabaseService:
        ...     pass
    """
    return injectable(Lifetime.SINGLETON)(cls)


def transient(cls: type) -> type:
    """标记类为瞬时服务.

    每次解析时都创建新的实例.

    Args:
        cls: 要装饰的类

    Returns:
        装饰后的类

    Examples:
        >>> @transient
        ... class RequestHandler:
        ...     pass
    """
    return injectable(Lifetime.TRANSIENT)(cls)


def scoped(cls: type) -> type:
    """标记类为作用域服务.

    在同一作用域内共享实例.

    Args:
        cls: 要装饰的类

    Returns:
        装饰后的类

    Examples:
        >>> @scoped
        ... class DbContextService:
        ...     pass
    """
    return injectable(Lifetime.SCOPED)(cls)


def factory(
    lifetime_or_func: Lifetime | Callable[..., T] = Lifetime.TRANSIENT,
    *,
    key: Any | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]] | Callable[..., T]:
    """标记函数为工厂函数.

    既支持无参用法 `@factory`，也支持参数化用法 `@factory(...)`。

    Args:
        lifetime_or_func: 生命周期或被装饰的函数(无参用法时)
        key: 服务键

    Returns:
        装饰器函数或已装饰的函数(无参用法)
    """
    # 无参用法: 直接传入函数 `@factory`
    if inspect.isfunction(lifetime_or_func) and not isinstance(lifetime_or_func, Lifetime):
        func = lifetime_or_func  # type: ignore[assignment]
        service_key = key or func.__name__
        metadata = ServiceMetadata(
            service_type=func,
            lifetime=Lifetime.TRANSIENT,
            key=service_key,
        )
        func.__symphra_metadata__ = metadata  # type: ignore[attr-defined]
        return func

    # 参数化用法: `@factory(...)`
    lifetime = lifetime_or_func if isinstance(lifetime_or_func, Lifetime) else Lifetime.TRANSIENT

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        service_key = key or func.__name__
        metadata = ServiceMetadata(
            service_type=func,
            lifetime=lifetime,
            key=service_key,
        )
        func.__symphra_metadata__ = metadata  # type: ignore[attr-defined]
        return func

    return decorator


def is_injectable(cls_or_func: Any) -> bool:
    """检查类或函数是否标记为 injectable.

    Args:
        cls_or_func: 要检查的类或函数

    Returns:
        是否标记为 injectable
    """
    return hasattr(cls_or_func, "__symphra_metadata__")


def get_service_metadata(cls_or_func: Any) -> ServiceMetadata | None:
    """获取服务的元数据.

    Args:
        cls_or_func: 类或函数

    Returns:
        元数据或 None
    """
    if not is_injectable(cls_or_func):
        return None
    return getattr(cls_or_func, "__symphra_metadata__", None)


def auto_register(
    container: Any,
    *classes: type,
    lifetime: Lifetime | None = None,
    key: Any | None = None,
):
    """自动注册标记为 injectable 或 factory 的服务。

    提供两种用法：
    1) 直接传入类列表进行注册：auto_register(container, ServiceA, ServiceB)
    2) 作为装饰器使用：@auto_register(container, lifetime=..., key=...)

    - 当作为装饰器时，会立即把被装饰的类/函数注册到容器中；
    - 对于被 @factory 装饰的函数，自动使用 register_factory；
    - 对于被 @injectable/@singleton/@transient/@scoped 装饰的类，使用 register；
    - 未装饰的类按默认生命周期（可通过 lifetime 参数覆盖）注册。
    """
    # 直接注册传入的类列表（非装饰器模式）
    if classes:
        for cls in classes:
            metadata = get_service_metadata(cls)
            if metadata:
                # 允许通过参数覆盖 key/lifetime（若提供）
                reg_key = key if key is not None else metadata.key
                reg_lifetime = metadata.lifetime if lifetime is None else lifetime
                # factory 装饰的对象是函数，需要走工厂注册
                if inspect.isfunction(metadata.service_type):
                    container.register_factory(reg_key or getattr(cls, "__name__", "factory"), metadata.service_type, lifetime=reg_lifetime)
                else:
                    container.register(metadata.service_type, key=reg_key, lifetime=reg_lifetime)
            else:
                container.register(cls, key=key, lifetime=lifetime or Lifetime.TRANSIENT)
        return None

    # 返回装饰器（装饰器模式）
    def decorator(cls_or_func: Any) -> Any:
        metadata = get_service_metadata(cls_or_func)
        if metadata:
            reg_key = key if key is not None else metadata.key
            reg_lifetime = metadata.lifetime if lifetime is None else lifetime
            if inspect.isfunction(metadata.service_type):
                # 工厂函数：使用 register_factory
                container.register_factory(reg_key or getattr(cls_or_func, "__name__", "factory"), cls_or_func, lifetime=reg_lifetime)
            else:
                # 类：使用常规 register
                container.register(metadata.service_type, key=reg_key, lifetime=reg_lifetime)
        else:
            # 未装饰：按传入的生命周期注册
            container.register(cls_or_func, key=key, lifetime=lifetime or Lifetime.TRANSIENT)
        return cls_or_func

    return decorator


# 导出所有装饰器
__all__ = [
    "ServiceMetadata",
    "auto_register",
    "factory",
    "get_service_metadata",
    "injectable",
    "is_injectable",
    "scoped",
    "singleton",
    "transient",
]
