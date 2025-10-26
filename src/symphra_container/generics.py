"""泛型类型支持.

提供泛型类型参数的区分和注册，使得 Repository[User] 和 Repository[Order]
可以被识别为不同的服务键。

示例:
    >>> from typing import Generic, TypeVar
    >>> from symphra_container import Container
    >>> from symphra_container.generics import register_generic
    >>>
    >>> T = TypeVar('T')
    >>>
    >>> class Repository(Generic[T]):
    ...     def get(self, id: int) -> T:
    ...         pass
    >>>
    >>> class User:
    ...     pass
    >>>
    >>> class UserRepository(Repository[User]):
    ...     def get(self, id: int) -> User:
    ...         return User()
    >>>
    >>> container = Container()
    >>> register_generic(container, Repository[User], UserRepository)
    >>> user_repo = container.resolve(Repository[User])
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, get_args, get_origin

if TYPE_CHECKING:
    from symphra_container.container import Container


__all__ = ["GenericKey", "register_generic", "resolve_generic"]

T = TypeVar("T")


class GenericKey:
    """泛型类型键.

    用于区分不同参数的泛型类型，例如 Repository[User] 和 Repository[Order]。

    Attributes:
        origin: 泛型基类 (例如 Repository)
        args: 类型参数 (例如 (User,))

    示例:
        >>> key1 = GenericKey(Repository, (User,))
        >>> key2 = GenericKey(Repository, (Order,))
        >>> key1 == key2  # False
        >>> key1 == GenericKey(Repository, (User,))  # True
    """

    def __init__(self, origin: type, args: tuple[type, ...]) -> None:
        """初始化泛型键.

        Args:
            origin: 泛型基类
            args: 类型参数元组
        """
        self.origin = origin
        self.args = args

    def __eq__(self, other: object) -> bool:
        """判断相等."""
        if not isinstance(other, GenericKey):
            return False
        return self.origin == other.origin and self.args == other.args

    def __hash__(self) -> int:
        """计算哈希值."""
        return hash((self.origin, self.args))

    def __repr__(self) -> str:
        """字符串表示."""
        args_str = ", ".join(arg.__name__ for arg in self.args)
        return f"{self.origin.__name__}[{args_str}]"


def _extract_generic_info(generic_type: Any) -> GenericKey | None:
    """提取泛型类型信息.

    Args:
        generic_type: 泛型类型，例如 Repository[User]

    Returns:
        GenericKey 或 None（如果不是泛型类型）

    示例:
        >>> info = _extract_generic_info(Repository[User])
        >>> info.origin  # Repository
        >>> info.args  # (User,)
    """
    origin = get_origin(generic_type)
    if origin is None:
        return None

    args = get_args(generic_type)
    if not args:
        return None

    return GenericKey(origin, args)


def register_generic(
    container: Container,
    generic_type: Any,
    implementation: type | None = None,
    factory: Any = None,
    lifetime: Any = None,
) -> None:
    """注册泛型服务.

    支持区分不同类型参数的泛型服务。

    Args:
        container: 容器实例
        generic_type: 泛型类型，例如 Repository[User]
        implementation: 实现类（可选）
        factory: 工厂函数（可选）
        lifetime: 生命周期（可选）

    Raises:
        ValueError: 如果不是有效的泛型类型

    示例:
        >>> register_generic(container, Repository[User], UserRepository)
        >>> register_generic(container, Repository[Order], OrderRepository)
        >>> register_generic(
        ...     container,
        ...     Repository[Product],
        ...     factory=lambda: ProductRepository()
        ... )
    """
    from .types import Lifetime as LifetimeEnum

    generic_key = _extract_generic_info(generic_type)
    if generic_key is None:
        msg = f"Not a valid generic type: {generic_type}"
        raise ValueError(msg)

    # 使用 GenericKey 作为服务键
    if factory:
        container.register_factory(
            generic_key,  # type: ignore
            factory,
            lifetime=lifetime or LifetimeEnum.TRANSIENT,
        )
    elif implementation:
        container.register(
            implementation,
            key=generic_key,  # type: ignore
            lifetime=lifetime or LifetimeEnum.TRANSIENT,
        )
    else:
        msg = "Either implementation or factory must be provided"
        raise ValueError(msg)


def resolve_generic(container: Container, generic_type: Any) -> Any:
    """解析泛型服务.

    Args:
        container: 容器实例
        generic_type: 泛型类型，例如 Repository[User]

    Returns:
        解析的服务实例

    Raises:
        ValueError: 如果不是有效的泛型类型
        ServiceNotFoundError: 如果服务未注册

    示例:
        >>> user_repo = resolve_generic(container, Repository[User])
        >>> order_repo = resolve_generic(container, Repository[Order])
    """
    generic_key = _extract_generic_info(generic_type)
    if generic_key is None:
        msg = f"Not a valid generic type: {generic_type}"
        raise ValueError(msg)

    return container.resolve(generic_key)  # type: ignore


def is_generic_type(type_hint: Any) -> bool:
    """检查是否为泛型类型.

    Args:
        type_hint: 类型提示

    Returns:
        True 如果是泛型类型

    示例:
        >>> is_generic_type(Repository[User])  # True
        >>> is_generic_type(Repository)  # False
        >>> is_generic_type(User)  # False
    """
    return get_origin(type_hint) is not None and get_args(type_hint) != ()
