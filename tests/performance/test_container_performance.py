"""Container 核心功能性能测试.

测试 Container 类的各种核心操作的性能表现:
- 服务注册性能
- 服务解析性能(各种生命周期)
- 依赖注入性能
- 作用域管理性能
- 大规模服务管理性能
"""

import time

import pytest

from symphra_container import (
    Container,
    Lifetime,
    Scope,
    injectable,
    singleton,
    transient,
)

# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def container():
    """创建一个干净的容器实例."""
    return Container()


@pytest.fixture
def simple_service():
    """简单服务类(无依赖)."""

    class SimpleService:
        def __init__(self) -> None:
            self.created_at = time.time()

    return SimpleService


@pytest.fixture
def service_with_deps():
    """带依赖的服务类."""

    class Database:
        pass

    class Cache:
        pass

    class UserService:
        def __init__(self, db: Database, cache: Cache) -> None:
            self.db = db
            self.cache = cache

    return UserService, Database, Cache


# ============================================================================
# 服务注册性能测试
# ============================================================================


def test_register_singleton_performance(benchmark, container, simple_service):
    """测试注册单例服务的性能."""

    def register():
        c = Container()
        for i in range(10):
            c.register(simple_service, key=f"service_{i}", lifetime=Lifetime.SINGLETON, override=True)
        return c

    result = benchmark(register)
    assert len(result._registrations) == 10


def test_register_transient_performance(benchmark, container, simple_service):
    """测试注册瞬态服务的性能."""

    def register():
        c = Container()
        for i in range(10):
            c.register(simple_service, key=f"service_{i}", lifetime=Lifetime.TRANSIENT, override=True)
        return c

    result = benchmark(register)
    assert len(result._registrations) == 10


def test_register_with_decorator_performance(benchmark):
    """测试使用装饰器注册服务的性能."""

    def register():
        container = Container()

        @singleton
        class Service1:
            pass

        @transient
        class Service2:
            pass

        @injectable
        class Service3:
            pass

        container.register(Service1)
        container.register(Service2)
        container.register(Service3)
        return container

    result = benchmark(register)
    assert len(result._registrations) >= 3


def test_register_with_factory_performance(benchmark, container):
    """测试注册工厂函数的性能."""

    class Config:
        def __init__(self, value: str) -> None:
            self.value = value

    def register():
        c = Container()
        for i in range(10):
            c.register_factory(
                f"config_{i}",
                lambda i=i: Config(f"value_{i}"),
                lifetime=Lifetime.SINGLETON,
            )
        return c

    result = benchmark(register)
    assert len(result._registrations) == 10


# ============================================================================
# 服务解析性能测试
# ============================================================================


def test_resolve_singleton_performance(benchmark, container, simple_service):
    """测试解析单例服务的性能(带缓存)."""
    container.register(simple_service, key="service", lifetime=Lifetime.SINGLETON)

    # 第一次解析会创建实例并缓存
    first = container.resolve("service")

    # 性能测试解析已缓存的单例
    result = benchmark(lambda: container.resolve("service"))
    assert result is first  # 应该返回同一个实例


def test_resolve_singleton_first_time_performance(benchmark, simple_service):
    """测试首次解析单例服务的性能(无缓存)."""

    def resolve():
        c = Container()
        c.register(simple_service, key="service", lifetime=Lifetime.SINGLETON)
        return c.resolve("service")

    result = benchmark(resolve)
    assert result is not None


def test_resolve_transient_performance(benchmark, container, simple_service):
    """测试解析瞬态服务的性能(每次创建新实例)."""
    container.register(simple_service, key="service", lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve("service"))
    assert result is not None


def test_resolve_with_dependencies_performance(benchmark, container, service_with_deps):
    """测试解析带依赖的服务的性能."""
    UserService, Database, Cache = service_with_deps

    container.register(Database, lifetime=Lifetime.SINGLETON)
    container.register(Cache, lifetime=Lifetime.SINGLETON)
    container.register(UserService, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(UserService))
    assert result is not None
    assert hasattr(result, "db")
    assert hasattr(result, "cache")


def test_resolve_deep_dependencies_performance(benchmark, container):
    """测试解析深层依赖链的性能."""

    class Level1:
        pass

    class Level2:
        def __init__(self, l1: Level1) -> None:
            self.l1 = l1

    class Level3:
        def __init__(self, l2: Level2) -> None:
            self.l2 = l2

    class Level4:
        def __init__(self, l3: Level3) -> None:
            self.l3 = l3

    class Level5:
        def __init__(self, l4: Level4) -> None:
            self.l4 = l4

    container.register(Level1, lifetime=Lifetime.SINGLETON)
    container.register(Level2, lifetime=Lifetime.SINGLETON)
    container.register(Level3, lifetime=Lifetime.SINGLETON)
    container.register(Level4, lifetime=Lifetime.SINGLETON)
    container.register(Level5, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(Level5))
    assert result is not None
    assert hasattr(result, "l4")
    assert hasattr(result.l4, "l3")


def test_resolve_multiple_services_performance(benchmark, container):
    """测试批量解析多个服务的性能."""

    class Service1:
        pass

    class Service2:
        pass

    class Service3:
        pass

    class Service4:
        pass

    class Service5:
        pass

    container.register(Service1, lifetime=Lifetime.SINGLETON)
    container.register(Service2, lifetime=Lifetime.SINGLETON)
    container.register(Service3, lifetime=Lifetime.SINGLETON)
    container.register(Service4, lifetime=Lifetime.SINGLETON)
    container.register(Service5, lifetime=Lifetime.SINGLETON)

    def resolve_all():
        return [
            container.resolve(Service1),
            container.resolve(Service2),
            container.resolve(Service3),
            container.resolve(Service4),
            container.resolve(Service5),
        ]

    result = benchmark(resolve_all)
    assert len(result) == 5


# ============================================================================
# 作用域管理性能测试
# ============================================================================


def test_scope_creation_performance(benchmark, container):
    """测试创建作用域的性能."""
    result = benchmark(lambda: container.create_scope())
    assert isinstance(result, Scope)


def test_scoped_service_resolution_performance(benchmark, container):
    """测试在作用域内解析服务的性能."""

    class ScopedService:
        pass

    container.register(ScopedService, lifetime=Lifetime.SCOPED)

    def resolve_in_scope():
        with container.create_scope() as scope:
            return scope.resolve(ScopedService)

    result = benchmark(resolve_in_scope)
    assert result is not None


def test_multiple_scopes_performance(benchmark, container):
    """测试管理多个作用域的性能."""

    class ScopedService:
        pass

    container.register(ScopedService, lifetime=Lifetime.SCOPED)

    def resolve_scoped():
        with container.create_scope():
            for _ in range(1000):
                service = container.resolve(ScopedService)

    benchmark(resolve_scoped)


# ============================================================================
# 大规模服务管理性能测试
# ============================================================================


def test_large_scale_registration_performance(benchmark):
    """测试大规模服务注册的性能(100个服务)."""

    def register_many():
        container = Container()
        for i in range(100):

            class Service:
                pass

            container.register(Service, key=f"service_{i}", lifetime=Lifetime.SINGLETON)
        return container

    result = benchmark(register_many)
    assert len(result._registrations) == 100


def test_large_scale_resolution_performance(benchmark):
    """测试大规模服务解析的性能."""
    container = Container()

    # 注册100个服务
    services = []
    for i in range(100):

        class Service:
            pass

        container.register(Service, key=f"service_{i}", lifetime=Lifetime.SINGLETON)
        services.append(f"service_{i}")

    # 测试解析所有服务
    def resolve_all():
        return [container.resolve(key) for key in services]

    result = benchmark(resolve_all)
    assert len(result) == 100


def test_mixed_lifetime_resolution_performance(benchmark):
    """测试混合生命周期服务解析的性能."""
    container = Container()

    # 注册不同生命周期的服务
    class SingletonService:
        pass

    class TransientService:
        pass

    class ScopedService:
        pass

    for i in range(10):
        container.register(SingletonService, key=f"singleton_{i}", lifetime=Lifetime.SINGLETON)
        container.register(TransientService, key=f"transient_{i}", lifetime=Lifetime.TRANSIENT)
        container.register(ScopedService, key=f"scoped_{i}", lifetime=Lifetime.SCOPED)

    def resolve_mixed():
        results = []
        with container.create_scope() as scope:
            for i in range(10):
                results.append(container.resolve(f"singleton_{i}"))
                results.append(container.resolve(f"transient_{i}"))
                results.append(scope.resolve(f"scoped_{i}"))
        return results

    result = benchmark(resolve_mixed)
    assert len(result) == 30


# ============================================================================
# 类型键 vs 字符串键性能对比
# ============================================================================


def test_type_key_resolution_performance(benchmark, container, simple_service):
    """测试使用类型作为键的解析性能."""
    container.register(simple_service, lifetime=Lifetime.SINGLETON)
    result = benchmark(lambda: container.resolve(simple_service))
    assert result is not None


def test_string_key_resolution_performance(benchmark, container, simple_service):
    """测试使用字符串作为键的解析性能."""
    container.register(simple_service, key="service", lifetime=Lifetime.SINGLETON)
    result = benchmark(lambda: container.resolve("service"))
    assert result is not None


def test_mixed_key_resolution_performance(benchmark, container):
    """测试混合使用类型键和字符串键的性能."""

    class Service1:
        pass

    class Service2:
        pass

    container.register(Service1, lifetime=Lifetime.SINGLETON)
    container.register(Service2, key="service2", lifetime=Lifetime.SINGLETON)

    def resolve_mixed():
        return [container.resolve(Service1), container.resolve("service2")]

    result = benchmark(resolve_mixed)
    assert len(result) == 2


# ============================================================================
# 容器克隆和子容器性能测试
# ============================================================================


def test_child_container_creation_performance(benchmark, container, simple_service):
    """测试创建子容器的性能."""
    container.register(simple_service, key="service", lifetime=Lifetime.SINGLETON)

    result = benchmark(lambda: container.create_scope())
    assert result is not None


def test_child_container_resolution_performance(benchmark, container, simple_service):
    """测试子容器解析服务的性能."""
    container.register(simple_service, key="service", lifetime=Lifetime.SINGLETON)
    def resolve_in_scope():
        with container.create_scope() as scope:
            return scope.resolve("service")

    result = benchmark(resolve_in_scope)
    assert result is not None


# ============================================================================
# 并发场景模拟性能测试
# ============================================================================


def test_concurrent_singleton_resolution_simulation(benchmark, container):
    """模拟并发解析单例服务的性能."""

    class SharedService:
        pass

    container.register(SharedService, lifetime=Lifetime.SINGLETON)

    # 模拟10个并发请求
    def simulate_concurrent():
        results = []
        for _ in range(10):
            results.append(container.resolve(SharedService))
        return results

    result = benchmark(simulate_concurrent)
    assert len(result) == 10
    # 所有结果应该是同一个实例
    assert len({id(r) for r in result}) == 1


def test_concurrent_transient_resolution_simulation(benchmark, container):
    """模拟并发解析瞬态服务的性能."""

    class PerRequestService:
        pass

    container.register(PerRequestService, lifetime=Lifetime.TRANSIENT)

    # 模拟10个并发请求
    def simulate_concurrent():
        results = []
        for _ in range(10):
            results.append(container.resolve(PerRequestService))
        return results

    result = benchmark(simulate_concurrent)
    assert len(result) == 10
    # 所有结果应该是不同的实例
    assert len({id(r) for r in result}) == 10


def test_concurrent_scoped_resolution_simulation(benchmark, container):
    """模拟并发解析作用域服务的性能."""

    class ScopedService:
        pass

    container.register(ScopedService, lifetime=Lifetime.SCOPED)

    # 模拟10个并发请求,每个请求有自己的作用域
    def simulate_concurrent():
        results = []
        for _ in range(10):
            with container.create_scope() as scope:
                results.append(scope.resolve(ScopedService))
        return results

    result = benchmark(simulate_concurrent)
    assert len(result) == 10
    # 所有结果应该是不同的实例(不同作用域)
    assert len({id(r) for r in result}) == 10


# ============================================================================
# 内存效率测试
# ============================================================================


def test_memory_efficiency_singleton_caching(benchmark, container):
    """测试单例缓存的内存效率."""

    class LargeService:
        def __init__(self) -> None:
            self.data = [0] * 1000  # 模拟大对象

    container.register(LargeService, lifetime=Lifetime.SINGLETON)

    # 多次解析,应该只创建一个实例
    def resolve_many():
        return [container.resolve(LargeService) for _ in range(100)]

    result = benchmark(resolve_many)
    assert len(result) == 100
    # 验证所有引用指向同一个对象
    assert len({id(r) for r in result}) == 1


def test_registration_overhead_performance(benchmark):
    """测试服务注册的内存开销."""

    def register_and_measure():
        container = Container()
        services = []

        for i in range(50):

            class Service:
                pass

            container.register(Service, key=f"service_{i}", lifetime=Lifetime.SINGLETON)
            services.append(Service)

        return container, services

    result, services = benchmark(register_and_measure)
    assert len(result._registrations) == 50


# ============================================================================
# 性能指标基准测试
# ============================================================================


def test_performance_baseline_simple_resolution(benchmark, container, simple_service):
    """建立简单服务解析的性能基准."""
    container.register(simple_service, key="service", lifetime=Lifetime.SINGLETON)

    # 预热
    container.resolve("service")

    # 基准测试: 应该 < 1 μs (已缓存的单例)
    result = benchmark(lambda: container.resolve("service"))
    assert result is not None


def test_performance_baseline_complex_resolution(benchmark, container):
    """建立复杂服务解析的性能基准."""

    class Dep1:
        pass

    class Dep2:
        pass

    class Dep3:
        pass

    class ComplexService:
        def __init__(self, d1: Dep1, d2: Dep2, d3: Dep3) -> None:
            self.d1 = d1
            self.d2 = d2
            self.d3 = d3

    container.register(Dep1, lifetime=Lifetime.SINGLETON)
    container.register(Dep2, lifetime=Lifetime.SINGLETON)
    container.register(Dep3, lifetime=Lifetime.SINGLETON)
    container.register(ComplexService, lifetime=Lifetime.TRANSIENT)

    # 基准测试: 应该 < 100 μs (带依赖注入的瞬态服务)
    result = benchmark(lambda: container.resolve(ComplexService))
    assert result is not None
    assert hasattr(result, "d1")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])