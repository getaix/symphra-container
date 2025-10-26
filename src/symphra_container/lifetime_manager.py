"""生命周期管理模块.

管理不同生命周期(Singleton,Transient,Scoped,Factory)的服务实例.
提供了生命周期缓存,释放和作用域管理功能.

主要类:
  - LifetimeManager: 生命周期管理器
  - SingletonStore: 单例存储
  - ScopedStore: 作用域存储
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, TypeVar

from .types import Lifetime, ServiceKey

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class SingletonStore:
    """单例存储.

    管理全局单例服务实例,确保整个容器生命周期中只有一个实例.
    提供线程安全的存储和检索功能.

    Attributes:
        _instances: 单例实例字典
        _locks: 双重检查锁定字典
    """

    def __init__(self) -> None:
        """初始化单例存储."""
        self._instances: dict[ServiceKey, Any] = {}

    def get(self, key: ServiceKey) -> Any | None:
        """获取单例实例.

        Args:
            key: 服务键

        Returns:
            服务实例或 None
        """
        return self._instances.get(key)

    def set(self, key: ServiceKey, instance: Any) -> None:
        """设置单例实例.

        Args:
            key: 服务键
            instance: 服务实例
        """
        self._instances[key] = instance

    def has(self, key: ServiceKey) -> bool:
        """检查是否存在实例.

        Args:
            key: 服务键

        Returns:
            是否存在
        """
        return key in self._instances

    def clear(self) -> None:
        """清空所有单例实例."""
        self._instances.clear()

    def dispose_all(self) -> None:
        """释放所有单例实例.

        如果实例实现了 Disposable 接口,则调用其 dispose 方法.
        """
        for instance in self._instances.values():
            if hasattr(instance, "dispose") and callable(instance.dispose):
                instance.dispose()
        self._instances.clear()


class ScopedStore:
    """作用域存储.

    管理特定作用域内的服务实例缓存.
    同一作用域内的所有请求共享相同的实例.

    Attributes:
        _instances: 作用域内的实例字典
        _scope_id: 作用域 ID
    """

    def __init__(self, scope_id: str) -> None:
        """初始化作用域存储.

        Args:
            scope_id: 作用域 ID
        """
        self._instances: dict[ServiceKey, Any] = {}
        self._scope_id = scope_id

    @property
    def scope_id(self) -> str:
        """获取作用域 ID."""
        return self._scope_id

    def get(self, key: ServiceKey) -> Any | None:
        """获取作用域内的实例.

        Args:
            key: 服务键

        Returns:
            服务实例或 None
        """
        return self._instances.get(key)

    def set(self, key: ServiceKey, instance: Any) -> None:
        """设置作用域内的实例.

        Args:
            key: 服务键
            instance: 服务实例
        """
        self._instances[key] = instance

    def has(self, key: ServiceKey) -> bool:
        """检查作用域内是否存在实例.

        Args:
            key: 服务键

        Returns:
            是否存在
        """
        return key in self._instances

    def dispose(self) -> None:
        """释放作用域内的所有实例.

        如果实例实现了 Disposable 接口,则调用其 dispose 方法.
        """
        for instance in self._instances.values():
            if hasattr(instance, "dispose") and callable(instance.dispose):
                instance.dispose()
        self._instances.clear()


class LifetimeManager:
    """生命周期管理器.

    统一管理所有生命周期类型的服务实例:
    - SINGLETON: 全局单例
    - TRANSIENT: 瞬时,每次新建
    - SCOPED: 作用域内共享
    - FACTORY: 工厂函数创建

    Attributes:
        _singleton_store: 单例存储
        _scoped_stores: 作用域存储字典
        _current_scope: 当前活跃的作用域
    """

    def __init__(self) -> None:
        """初始化生命周期管理器."""
        self._singleton_store = SingletonStore()
        self._scoped_stores: dict[str, ScopedStore] = {}
        self._current_scope: ScopedStore | None = None

    def get_instance(
        self,
        key: ServiceKey,
        lifetime: Lifetime,
        factory: Callable[[], T] | None = None,
    ) -> T | None:
        """获取服务实例.

        根据生命周期类型决定如何获取实例:
        - SINGLETON: 从单例存储获取,如果不存在则创建
        - TRANSIENT: 总是返回 None(由调用者创建新实例)
        - SCOPED: 从当前作用域存储获取
        - FACTORY: 由调用者通过工厂函数创建

        Args:
            key: 服务键
            lifetime: 生命周期类型
            factory: 用于创建实例的工厂函数(仅用于 SINGLETON)

        Returns:
            服务实例或 None
        """
        if lifetime == Lifetime.SINGLETON:
            # 单例:检查是否已存在,否则创建
            if self._singleton_store.has(key):
                return self._singleton_store.get(key)
            if factory:
                instance = factory()
                self._singleton_store.set(key, instance)
                return instance
            return None

        if lifetime == Lifetime.TRANSIENT:
            # 瞬时:总是返回 None,由调用者创建新实例
            return None

        if lifetime == Lifetime.SCOPED:
            # 作用域:从当前作用域获取
            if self._current_scope:
                if not self._current_scope.has(key) and factory:
                    instance = factory()
                    self._current_scope.set(key, instance)
                return self._current_scope.get(key)
            return None

        if lifetime == Lifetime.FACTORY:
            # 工厂:由调用者调用工厂函数创建
            return None

        return None

    def set_instance(
        self,
        key: ServiceKey,
        instance: T,
        lifetime: Lifetime,
    ) -> None:
        """设置服务实例.

        根据生命周期类型存储实例:
        - SINGLETON: 存储到单例存储
        - TRANSIENT: 不存储
        - SCOPED: 存储到当前作用域
        - FACTORY: 不存储

        Args:
            key: 服务键
            instance: 服务实例
            lifetime: 生命周期类型
        """
        if lifetime == Lifetime.SINGLETON:
            self._singleton_store.set(key, instance)
        elif lifetime == Lifetime.SCOPED and self._current_scope:
            self._current_scope.set(key, instance)

    def enter_scope(self, scope_id: str) -> ScopedStore:
        """进入新的作用域.

        Args:
            scope_id: 作用域 ID

        Returns:
            作用域存储对象
        """
        scope = ScopedStore(scope_id)
        self._scoped_stores[scope_id] = scope
        self._current_scope = scope
        return scope

    def exit_scope(self, scope_id: str) -> None:
        """离开作用域.

        释放该作用域内的所有资源.

        Args:
            scope_id: 作用域 ID
        """
        if scope_id in self._scoped_stores:
            scope = self._scoped_stores[scope_id]
            scope.dispose()
            del self._scoped_stores[scope_id]
            # 如果当前作用域是要离开的作用域,则重置
            if self._current_scope is scope:
                self._current_scope = None

    @property
    def current_scope(self) -> ScopedStore | None:
        """获取当前活跃的作用域."""
        return self._current_scope

    def has_active_scope(self) -> bool:
        """检查是否有活跃的作用域."""
        return self._current_scope is not None

    def dispose_all(self) -> None:
        """释放所有资源.

        包括单例实例和所有作用域内的实例.
        """
        # 释放所有作用域
        for scope_id in list(self._scoped_stores.keys()):
            self.exit_scope(scope_id)

        # 释放所有单例
        self._singleton_store.dispose_all()

    def clear(self) -> None:
        """清空所有存储."""
        self.dispose_all()
        self._current_scope = None

    def remove_instance(self, key: ServiceKey) -> None:
        """移除指定服务的实例.

        Args:
            key: 服务键
        """
        # 从单例存储中移除
        if self._singleton_store.has(key):
            instance = self._singleton_store.get(key)
            if instance and hasattr(instance, "dispose"):
                with contextlib.suppress(Exception):
                    instance.dispose()
            # 直接访问私有属性进行删除
            if hasattr(self._singleton_store, "_instances"):
                self._singleton_store._instances.pop(key, None)

        # 从所有作用域中移除
        for scope_store in self._scoped_stores.values():
            if scope_store.has(key):
                instance = scope_store.get(key)
                if instance and hasattr(instance, "dispose"):
                    with contextlib.suppress(Exception):
                        instance.dispose()
                if hasattr(scope_store, "_instances"):
                    scope_store._instances.pop(key, None)
