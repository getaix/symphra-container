"""循环依赖检测和处理模块.

提供循环依赖的自动检测,错误报告和 Lazy Proxy 机制来解决循环依赖问题.

主要类:
  - CircularDependencyDetector: 循环依赖检测器
  - LazyProxy: 懒加载代理,用于打破循环依赖
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from .exceptions import CircularDependencyError


class CircularDependencyDetector:
    """循环依赖检测器.

    在容器解析服务时跟踪依赖链,自动检测循环依赖.

    Attributes:
        _resolution_stack: 当前解析的服务栈
        _visited: 已访问的服务集合
        _recursion_limit: 最大递归深度(防止无限循环)
    """

    def __init__(self, max_depth: int = 1000) -> None:
        """初始化循环依赖检测器.

        Args:
            max_depth: 最大递归深度,默认 1000
        """
        self._resolution_stack: list[Any] = []
        self._visited: set[Any] = set()
        self._recursion_limit = max_depth

    # 保留先前实现的 push/pop 接口
    def push(self, key: Any) -> None:
        """压入解析栈并检测循环.

        Args:
            key: 当前正在解析的服务键

        Raises:
            CircularDependencyError: 检测到循环依赖
        """
        # 防止无限递归
        if len(self._resolution_stack) >= self._recursion_limit:
            raise CircularDependencyError(key, self._resolution_stack.copy())

        # 如果重复解析同一个键,说明存在循环依赖
        if key in self._resolution_stack:
            raise CircularDependencyError(key, self._resolution_stack.copy())

        self._resolution_stack.append(key)
        self._visited.add(key)

    def pop(self) -> None:
        """弹出解析栈顶元素."""
        if self._resolution_stack:
            self._resolution_stack.pop()

    def clear(self) -> None:
        """清空解析状态."""
        self._resolution_stack.clear()
        self._visited.clear()

    def reset(self) -> None:
        """重置检测器状态(与 clear 相同,用于测试兼容性)."""
        self.clear()

    @property
    def current_depth(self) -> int:
        """返回当前解析深度."""
        return len(self._resolution_stack)

    @property
    def chain(self) -> list[Any]:
        """返回当前依赖链的副本."""
        return self._resolution_stack.copy()

    # 与容器的接口保持兼容
    def enter_resolution(self, key: Any) -> None:
        """进入解析流程(兼容容器调用)."""
        self.push(key)

    def exit_resolution(self, key: Any | None = None) -> None:
        """退出解析流程(兼容容器调用)."""
        self.pop()


class LazyTypeMarker:
    """Lazy 类型标记.

    用于在类型注解中表达 Lazy[T] 结构,使得 typing.get_type_hints
    可以成功解析形如 Lazy[Service] 的注解。

    Attributes:
        inner_type: 被延迟解析的真实服务类型
    """

    def __init__(self, inner_type: Any) -> None:
        self.inner_type = inner_type

    def __repr__(self) -> str:
        try:
            name = getattr(self.inner_type, "__name__", repr(self.inner_type))
        except Exception:  # noqa: BLE001
            name = repr(self.inner_type)
        return f"Lazy[{name}]"


class LazyProxy:
    """懒加载代理.

    用于延迟解析依赖,从而打破循环依赖.
    当首次访问代理对象的属性或方法时,才会真正解析依赖.

    示例:
        >>> from symphra_container import Lazy
        >>> class ServiceA:
        ...     def __init__(self, b: Lazy["ServiceB"]):
        ...         self.b_lazy = b
        ...
        ...     def get_b(self):
        ...         return self.b_lazy()  # 调用代理以获取真实对象
        ...
        >>> class ServiceB:
        ...     def __init__(self, a: ServiceA):
        ...         self.a = a
        ...
        >>> container = Container()
        >>> container.register(ServiceA)
        >>> container.register(ServiceB)
        >>> a = container.resolve(ServiceA)
        >>> b = a.get_b()  # 此时 ServiceB 才被解析
        >>> assert isinstance(b, ServiceB)

    Attributes:
        _factory: 创建真实对象的工厂函数
        _cached_instance: 缓存的真实对象
        _proxy_id: 代理 ID
    """

    def __init__(self, factory: Callable[[], Any]) -> None:
        self._factory = factory
        self._cached_instance: Any | None = None
        self._proxy_id = uuid.uuid4()

    @classmethod
    def __class_getitem__(cls, item: Any) -> LazyTypeMarker:  # type: ignore[override]
        """支持 Lazy[T] 语法的类型标注.

        返回一个 LazyTypeMarker, 以便类型提示系统可以识别并保留
        T 的信息用于后续依赖注入阶段。
        """
        return LazyTypeMarker(item)

    def _get_real_instance(self) -> Any:
        """获取真实对象(带缓存)."""
        if self._cached_instance is None:
            self._cached_instance = self._factory()
        return self._cached_instance

    def __call__(self) -> Any:
        """调用代理以获取真实对象."""
        return self._get_real_instance()

    def __getattr__(self, name: str) -> Any:
        """代理属性访问到真实对象."""
        real = self._get_real_instance()
        return getattr(real, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_factory", "_cached_instance", "_proxy_id"}:
            object.__setattr__(self, name, value)
            return
        real = self._get_real_instance()
        setattr(real, name, value)

    def __repr__(self) -> str:
        """返回字符串表示."""
        return f"LazyProxy({object.__getattribute__(self, '_proxy_id')})"

    def __str__(self) -> str:
        """返回字符串表示."""
        return repr(self)

    def __getitem__(self, key: Any) -> Any:
        """代理下标访问到真实对象."""
        real = self._get_real_instance()
        return real[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        """代理下标设置到真实对象."""
        real = self._get_real_instance()
        real[key] = value

    def __len__(self) -> int:
        """代理长度计算到真实对象."""
        real = self._get_real_instance()
        return len(real)

    def __contains__(self, item: Any) -> bool:
        """代理包含检查到真实对象."""
        real = self._get_real_instance()
        return item in real


# 类型别名:可以在类型注解中使用 Lazy[T] 来表示懒加载的依赖
Lazy = LazyProxy
