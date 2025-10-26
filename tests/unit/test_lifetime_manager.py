"""生命周期管理器单元测试.

测试 LifetimeManager,SingletonStore 和 ScopedStore.
"""

from symphra_container.lifetime_manager import LifetimeManager, ScopedStore, SingletonStore
from symphra_container.types import Lifetime


class TestSingletonStore:
    """SingletonStore 测试."""

    def test_set_and_get(self) -> None:
        """测试设置和获取."""
        store = SingletonStore()
        store.set("key1", "value1")
        assert store.get("key1") == "value1"

    def test_has(self) -> None:
        """测试检查存在性."""
        store = SingletonStore()
        assert not store.has("key1")
        store.set("key1", "value1")
        assert store.has("key1")

    def test_clear(self) -> None:
        """测试清空存储."""
        store = SingletonStore()
        store.set("key1", "value1")
        store.clear()
        assert not store.has("key1")

    def test_dispose_all(self) -> None:
        """测试释放所有实例."""
        store = SingletonStore()

        class DisposableObject:
            def __init__(self) -> None:
                self.disposed = False

            def dispose(self) -> None:
                self.disposed = True

        obj = DisposableObject()
        store.set("key1", obj)
        store.dispose_all()

        assert obj.disposed is True
        assert not store.has("key1")

    def test_multiple_instances(self) -> None:
        """测试多个实例."""
        store = SingletonStore()
        store.set("key1", "value1")
        store.set("key2", "value2")
        store.set("key3", "value3")

        assert store.get("key1") == "value1"
        assert store.get("key2") == "value2"
        assert store.get("key3") == "value3"


class TestScopedStore:
    """ScopedStore 测试."""

    def test_scope_id(self) -> None:
        """测试作用域 ID."""
        store = ScopedStore("scope_1")
        assert store.scope_id == "scope_1"

    def test_set_and_get(self) -> None:
        """测试设置和获取."""
        store = ScopedStore("scope_1")
        store.set("key1", "value1")
        assert store.get("key1") == "value1"

    def test_has(self) -> None:
        """测试检查存在性."""
        store = ScopedStore("scope_1")
        assert not store.has("key1")
        store.set("key1", "value1")
        assert store.has("key1")

    def test_dispose(self) -> None:
        """测试释放作用域."""
        store = ScopedStore("scope_1")

        class DisposableObject:
            def __init__(self) -> None:
                self.disposed = False

            def dispose(self) -> None:
                self.disposed = True

        obj = DisposableObject()
        store.set("key1", obj)
        store.dispose()

        assert obj.disposed is True
        assert not store.has("key1")

    def test_multiple_instances_in_scope(self) -> None:
        """测试作用域内的多个实例."""
        store = ScopedStore("scope_1")
        store.set("key1", "value1")
        store.set("key2", "value2")

        assert store.get("key1") == "value1"
        assert store.get("key2") == "value2"


class TestLifetimeManager:
    """LifetimeManager 测试."""

    def test_get_instance_singleton_caching(self) -> None:
        """测试单例实例缓存."""
        manager = LifetimeManager()
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        result1 = manager.get_instance("key1", Lifetime.SINGLETON, factory)
        result2 = manager.get_instance("key1", Lifetime.SINGLETON, factory)

        assert result1 == "instance_1"
        assert result2 == "instance_1"
        assert call_count == 1  # 工厂只调用了一次

    def test_get_instance_transient(self) -> None:
        """测试瞬时实例."""
        manager = LifetimeManager()
        result = manager.get_instance("key1", Lifetime.TRANSIENT)
        assert result is None  # 瞬时返回 None

    def test_set_instance_singleton(self) -> None:
        """测试设置单例实例."""
        manager = LifetimeManager()
        manager.set_instance("key1", "value1", Lifetime.SINGLETON)
        result = manager.get_instance("key1", Lifetime.SINGLETON)
        assert result == "value1"

    def test_enter_and_exit_scope(self) -> None:
        """测试进入和离开作用域."""
        manager = LifetimeManager()
        scope = manager.enter_scope("scope_1")

        assert manager.has_active_scope()
        assert manager.current_scope is scope

        manager.exit_scope("scope_1")
        assert not manager.has_active_scope()

    def test_scoped_instance_in_scope(self) -> None:
        """测试作用域内的实例."""
        manager = LifetimeManager()
        manager.enter_scope("scope_1")

        manager.set_instance("key1", "value1", Lifetime.SCOPED)
        result = manager.get_instance("key1", Lifetime.SCOPED)

        assert result == "value1"

        manager.exit_scope("scope_1")

    def test_clear_all(self) -> None:
        """测试清空所有."""
        manager = LifetimeManager()

        # 设置单例
        manager.set_instance("key1", "value1", Lifetime.SINGLETON)
        assert manager.get_instance("key1", Lifetime.SINGLETON) == "value1"

        manager.clear()

        # 清空后应该没有实例
        result = manager.get_instance("key1", Lifetime.SINGLETON, lambda: "new")
        assert result == "new"

    def test_multiple_scopes(self) -> None:
        """测试多个作用域."""
        manager = LifetimeManager()

        # 作用域 1
        manager.enter_scope("scope_1")
        manager.set_instance("key1", "scope_1_value", Lifetime.SCOPED)
        assert manager.get_instance("key1", Lifetime.SCOPED) == "scope_1_value"
        manager.exit_scope("scope_1")

        # 作用域 2
        manager.enter_scope("scope_2")
        manager.set_instance("key1", "scope_2_value", Lifetime.SCOPED)
        assert manager.get_instance("key1", Lifetime.SCOPED) == "scope_2_value"
        manager.exit_scope("scope_2")

    def test_dispose_all(self) -> None:
        """测试释放所有资源."""
        manager = LifetimeManager()

        class DisposableObject:
            def __init__(self, name) -> None:
                self.name = name
                self.disposed = False

            def dispose(self) -> None:
                self.disposed = True

        # 设置单例
        obj1 = DisposableObject("obj1")
        manager.set_instance("key1", obj1, Lifetime.SINGLETON)

        # 设置作用域实例
        manager.enter_scope("scope_1")
        obj2 = DisposableObject("obj2")
        manager.set_instance("key2", obj2, Lifetime.SCOPED)
        manager.exit_scope("scope_1")

        # 释放所有
        manager.dispose_all()

        assert obj1.disposed is True
        assert obj2.disposed is True
