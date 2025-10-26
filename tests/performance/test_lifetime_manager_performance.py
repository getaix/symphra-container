"""生命周期管理器性能测试.

测试 LifetimeManager 的性能:
- 单例实例缓存
- 瞬态实例创建
- 作用域实例管理
- 资源释放性能
"""

import pytest

from symphra_container import Container, Lifetime
from symphra_container.lifetime_manager import LifetimeManager

# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def container():
    """创建容器实例."""
    return Container()


@pytest.fixture
def lifetime_manager():
    """创建生命周期管理器实例."""
    return LifetimeManager()


# ============================================================================
# 单例管理性能测试
# ============================================================================


def test_singleton_caching_performance(benchmark, container):
    """测试单例缓存的性能."""

    class SingletonService:
        pass

    container.register(SingletonService, lifetime=Lifetime.SINGLETON)

    # 第一次解析创建实例
    first = container.resolve(SingletonService)

    # 测试缓存访问性能
    result = benchmark(lambda: container.resolve(SingletonService))
    assert result is first


def test_singleton_cache_lookup_performance(benchmark, container):
    """测试单例缓存查找的性能."""

    class Service:
        pass

    container.register(Service, key="service", lifetime=Lifetime.SINGLETON)
    container.resolve("service")  # 预热缓存

    result = benchmark(lambda: container.resolve("service"))
    assert result is not None


def test_multiple_singleton_cache_performance(benchmark, container):
    """测试多个单例缓存的性能."""
    # 注册10个单例服务
    for i in range(10):

        class Service:
            pass

        container.register(Service, key=f"service_{i}", lifetime=Lifetime.SINGLETON)

    # 预热所有缓存
    for i in range(10):
        container.resolve(f"service_{i}")

    # 测试批量缓存访问
    def resolve_all():
        return [container.resolve(f"service_{i}") for i in range(10)]

    result = benchmark(resolve_all)
    assert len(result) == 10


# ============================================================================
# 瞬态实例创建性能测试
# ============================================================================


def test_transient_creation_performance(benchmark, container):
    """测试瞬态实例创建的性能."""

    class TransientService:
        pass

    container.register(TransientService, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(TransientService))
    assert result is not None


def test_transient_with_simple_init_performance(benchmark, container):
    """测试简单初始化的瞬态服务性能."""

    class Service:
        def __init__(self) -> None:
            self.value = 42

    container.register(Service, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(Service))
    assert result.value == 42


def test_transient_with_dependencies_performance(benchmark, container):
    """测试带依赖的瞬态服务性能."""

    class Dependency:
        pass

    class Service:
        def __init__(self, dep: Dependency) -> None:
            self.dep = dep

    container.register(Dependency, lifetime=Lifetime.SINGLETON)
    container.register(Service, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(Service))
    assert result is not None


def test_multiple_transient_creation_performance(benchmark, container):
    """测试批量创建瞬态实例的性能."""

    class Service:
        pass

    container.register(Service, lifetime=Lifetime.TRANSIENT)

    def create_many():
        return [container.resolve(Service) for _ in range(10)]

    result = benchmark(create_many)
    assert len(result) == 10
    # 验证都是不同实例
    assert len({id(r) for r in result}) == 10


# ============================================================================
# 作用域管理性能测试
# ============================================================================


def test_scoped_instance_creation_performance(benchmark, container):
    """测试作用域实例创建的性能."""

    class ScopedService:
        pass

    container.register(ScopedService, lifetime=Lifetime.SCOPED)
    with container.create_scope() as scope:
        result = benchmark(lambda: scope.resolve(ScopedService))
    assert result is not None


def test_scoped_instance_caching_performance(benchmark, container):
    """测试作用域内实例缓存的性能."""

    class ScopedService:
        pass

    container.register(ScopedService, lifetime=Lifetime.SCOPED)
    with container.create_scope() as scope:
        first = scope.resolve(ScopedService)

        # 测试同一作用域内的缓存访问 (保持作用域活动状态)
        def resolve_cached():
            return scope.resolve(ScopedService)

        result = benchmark(resolve_cached)
        assert result is first


def test_multiple_scopes_isolation_performance(benchmark, container):
    """测试多个作用域隔离的性能."""

    class ScopedService:
        pass

    container.register(ScopedService, lifetime=Lifetime.SCOPED)

    def create_scopes():
        scopes = []
        for _ in range(10):
            with container.create_scope() as scope:
                service = scope.resolve(ScopedService)
                scopes.append((scope, service))
        return scopes

    result = benchmark(create_scopes)
    assert len(result) == 10


# ============================================================================
# 生命周期切换性能测试
# ============================================================================


def test_mixed_lifetime_resolution_performance(benchmark, container):
    """测试混合生命周期解析的性能."""

    class SingletonService:
        pass

    class TransientService:
        def __init__(self, singleton: SingletonService) -> None:
            self.singleton = singleton

    class ScopedService:
        def __init__(self, transient: TransientService) -> None:
            self.transient = transient

    container.register(SingletonService, lifetime=Lifetime.SINGLETON)
    container.register(TransientService, lifetime=Lifetime.TRANSIENT)
    container.register(ScopedService, lifetime=Lifetime.SCOPED)

    with container.create_scope() as scope:
        result = benchmark(lambda: scope.resolve(ScopedService))
    assert result is not None


# ============================================================================
# 资源释放性能测试
# ============================================================================


def test_scope_disposal_performance(benchmark, container):
    """测试作用域释放的性能."""

    class DisposableService:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    container.register(DisposableService, lifetime=Lifetime.SCOPED)

    def create_and_dispose():
        with container.create_scope() as scope:
            scope.resolve(DisposableService)
            # 手动释放作用域（如果有 dispose 方法）
            return scope

    result = benchmark(create_and_dispose)
    assert result is not None


def test_multiple_disposables_performance(benchmark, container):
    """测试多个可释放服务的性能."""
    for i in range(10):

        class Service:
            def __init__(self) -> None:
                self.disposed = False

            def dispose(self) -> None:
                self.disposed = True

        container.register(Service, key=f"service_{i}", lifetime=Lifetime.SCOPED)

    def create_and_resolve():
        with container.create_scope() as scope:
            services = [scope.resolve(f"service_{i}") for i in range(10)]
            return scope, services

    result_scope, _ = benchmark(create_and_resolve)
    assert result_scope is not None


# ============================================================================
# 工厂生命周期性能测试
# ============================================================================


def test_factory_singleton_performance(benchmark, container):
    """测试工厂单例的性能."""
    call_count = 0

    def create_service():
        nonlocal call_count
        call_count += 1
        return {"id": call_count}

    container.register_factory("service", create_service, lifetime=Lifetime.SINGLETON)

    # 第一次调用工厂
    first = container.resolve("service")

    # 测试缓存访问
    result = benchmark(lambda: container.resolve("service"))
    assert result is first
    assert call_count == 1  # 工厂只应该调用一次


def test_factory_transient_performance(benchmark, container):
    """测试工厂瞬态的性能."""

    def create_service():
        return {"value": 42}

    container.register_factory("service", create_service, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve("service"))
    assert result is not None


# ============================================================================
# 大规模生命周期管理性能测试
# ============================================================================


def test_large_scale_singleton_management_performance(benchmark):
    """测试大规模单例管理的性能."""
    container = Container()

    # 注册100个单例服务
    for i in range(100):

        class Service:
            pass

        container.register(Service, key=f"service_{i}", lifetime=Lifetime.SINGLETON)

    # 预热所有缓存
    for i in range(100):
        container.resolve(f"service_{i}")

    # 测试访问性能
    def resolve_all():
        return [container.resolve(f"service_{i}") for i in range(100)]

    result = benchmark(resolve_all)
    assert len(result) == 100


def test_large_scale_transient_creation_performance(benchmark):
    """测试大规模瞬态创建的性能."""
    container = Container()

    class Service:
        pass

    container.register(Service, lifetime=Lifetime.TRANSIENT)

    # 创建100个实例
    def create_many():
        return [container.resolve(Service) for _ in range(100)]

    result = benchmark(create_many)
    assert len(result) == 100
    # 验证都是不同实例
    assert len({id(r) for r in result}) == 100


def test_large_scale_scoped_management_performance(benchmark):
    """测试大规模作用域管理的性能."""
    container = Container()

    class Service:
        pass

    container.register(Service, lifetime=Lifetime.SCOPED)

    # 创建100个作用域
    def create_scopes():
        results = []
        for _ in range(100):
            with container.create_scope() as scope:
                service = scope.resolve(Service)
                results.append(service)
        return results

    result = benchmark(create_scopes)
    assert len(result) == 100


# ============================================================================
# 生命周期管理器基准测试
# ============================================================================


def test_lifetime_manager_singleton_baseline(benchmark, container):
    """建立单例管理的性能基准."""

    class Service:
        pass

    container.register(Service, lifetime=Lifetime.SINGLETON)
    container.resolve(Service)  # 预热

    # 基准: 缓存访问应该 < 1 μs
    result = benchmark(lambda: container.resolve(Service))
    assert result is not None


def test_lifetime_manager_transient_baseline(benchmark, container):
    """建立瞬态创建的性能基准."""

    class Service:
        pass

    container.register(Service, lifetime=Lifetime.TRANSIENT)

    # 基准: 简单类实例化应该 < 10 μs
    result = benchmark(lambda: container.resolve(Service))
    assert result is not None


def test_lifetime_manager_scoped_baseline(benchmark, container):
    """建立作用域管理的性能基准."""

    class Service:
        pass

    container.register(Service, lifetime=Lifetime.SCOPED)
    with container.create_scope() as scope:
        scope.resolve(Service)  # 预热

        def resolve_scoped():
            return scope.resolve(Service)

        result = benchmark(resolve_scoped)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
