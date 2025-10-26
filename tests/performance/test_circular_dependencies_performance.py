"""循环依赖检测性能测试.

测试循环依赖检测机制的性能:
- 依赖图构建
- 循环检测算法
- Lazy 延迟解析
- 大规模依赖检测
"""

from __future__ import annotations

import pytest

from symphra_container import (
    CircularDependencyError,
    Container,
    Lazy,
    Lifetime,
)

# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def container():
    """创建容器实例."""
    from symphra_container.injector import ConstructorInjector

    # 清除依赖分析缓存，避免测试间干扰
    ConstructorInjector.clear_cache()
    return Container()


# ============================================================================
# 依赖检测性能测试
# ============================================================================


def test_simple_dependency_detection_performance(benchmark, container):
    """测试简单依赖关系检测的性能."""

    class ServiceA:
        pass

    class ServiceB:
        def __init__(self, a: ServiceA) -> None:
            self.a = a

    container.register(ServiceA, lifetime=Lifetime.SINGLETON)
    container.register(ServiceB, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(ServiceB))
    assert result is not None


def test_chain_dependency_detection_performance(benchmark, container):
    """测试链式依赖检测的性能."""

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


def test_complex_dependency_graph_detection_performance(benchmark, container):
    """测试复杂依赖图检测的性能."""

    class Database:
        pass

    class Cache:
        pass

    class Logger:
        pass

    class Config:
        pass

    class ServiceA:
        def __init__(self, db: Database, logger: Logger) -> None:
            self.db = db
            self.logger = logger

    class ServiceB:
        def __init__(self, cache: Cache, config: Config) -> None:
            self.cache = cache
            self.config = config

    class ServiceC:
        def __init__(self, a: ServiceA, b: ServiceB, logger: Logger) -> None:
            self.a = a
            self.b = b
            self.logger = logger

    container.register(Database, lifetime=Lifetime.SINGLETON)
    container.register(Cache, lifetime=Lifetime.SINGLETON)
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Config, lifetime=Lifetime.SINGLETON)
    container.register(ServiceA, lifetime=Lifetime.SINGLETON)
    container.register(ServiceB, lifetime=Lifetime.SINGLETON)
    container.register(ServiceC, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(ServiceC))
    assert result is not None


# ============================================================================
# 循环依赖检测性能测试
# ============================================================================


def test_circular_dependency_detection_performance(benchmark, container):
    """测试检测循环依赖的性能."""

    class ServiceA:
        def __init__(self, b: ServiceB) -> None:
            self.b = b

    class ServiceB:
        def __init__(self, a: ServiceA) -> None:
            self.a = a

    container.register(ServiceA, lifetime=Lifetime.TRANSIENT)
    container.register(ServiceB, lifetime=Lifetime.TRANSIENT)

    # 测试检测循环依赖的速度
    def detect_circular():
        try:
            container.resolve(ServiceA)
            return False
        except CircularDependencyError:
            return True

    result = benchmark(detect_circular)
    assert result is True


def test_indirect_circular_detection_performance(benchmark, container):
    """测试间接循环依赖检测的性能."""

    class ServiceA:
        def __init__(self, b: ServiceB) -> None:
            self.b = b

    class ServiceB:
        def __init__(self, c: ServiceC) -> None:
            self.c = c

    class ServiceC:
        def __init__(self, a: ServiceA) -> None:
            self.a = a

    container.register(ServiceA, lifetime=Lifetime.TRANSIENT)
    container.register(ServiceB, lifetime=Lifetime.TRANSIENT)
    container.register(ServiceC, lifetime=Lifetime.TRANSIENT)

    def detect_circular():
        try:
            container.resolve(ServiceA)
            return False
        except CircularDependencyError:
            return True

    result = benchmark(detect_circular)
    assert result is True


# ============================================================================
# Lazy 延迟解析性能测试
# ============================================================================


def test_lazy_resolution_performance(benchmark, container):
    """测试 Lazy 延迟解析的性能."""

    class ServiceA:
        pass

    class ServiceB:
        def __init__(self, a: Lazy[ServiceA]) -> None:
            self.a = a

    container.register(ServiceA, lifetime=Lifetime.SINGLETON)
    container.register(ServiceB, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(ServiceB))
    assert result is not None


def test_lazy_value_access_performance(benchmark, container):
    """测试访问 Lazy 值的性能."""

    class Service:
        def __init__(self) -> None:
            self.value = 42

    class Consumer:
        def __init__(self, service: Lazy[Service]) -> None:
            self.service = service

    container.register(Service, lifetime=Lifetime.SINGLETON)
    container.register(Consumer, lifetime=Lifetime.TRANSIENT)

    consumer = container.resolve(Consumer)

    # 测试访问 Lazy 值的性能
    result = benchmark(lambda: consumer.service.value)
    assert result == 42


def test_lazy_circular_resolution_performance(benchmark, container):
    """测试使用 Lazy 解决循环依赖的性能."""

    class ServiceA:
        def __init__(self, b: Lazy[ServiceB]) -> None:
            self.b = b

    class ServiceB:
        def __init__(self, a: Lazy[ServiceA]) -> None:
            self.a = a

    container.register(ServiceA, lifetime=Lifetime.SINGLETON)
    container.register(ServiceB, lifetime=Lifetime.SINGLETON)

    result = benchmark(lambda: container.resolve(ServiceA))
    assert result is not None


# ============================================================================
# 大规模依赖检测性能测试
# ============================================================================


def test_large_dependency_graph_detection_performance(benchmark):
    """测试大规模依赖图检测的性能."""
    container = Container()

    # 创建一个有50个服务的依赖图
    services = []
    for i in range(50):
        service_name = f"Service{i}"
        Service = type(service_name, (), {})
        services.append(Service)
        if i == 0:
            container.register(Service, lifetime=Lifetime.SINGLETON)
        else:
            # 依赖前一个服务
            prev_service = services[i - 1]

            DependentService = type(f"DependentService{i}", (), {
                '__init__': lambda self, dep: setattr(self, 'dep', dep)
            })

            # 设置注解
            DependentService.__init__.__annotations__ = {'dep': prev_service}

            container.register(DependentService, lifetime=Lifetime.SINGLETON)
            services[i] = DependentService

    # 解析最后一个服务（依赖链最长）
    last_service = services[-1]
    result = benchmark(lambda: container.resolve(last_service))
    assert result is not None


def test_wide_dependency_graph_performance(benchmark):
    """测试宽依赖图的性能."""
    container = Container()

    # 创建20个独立的基础服务
    base_services = []
    for i in range(20):

        class BaseService:
            pass

        container.register(BaseService, key=f"base_{i}", lifetime=Lifetime.SINGLETON)
        base_services.append(f"base_{i}")

    # 创建一个依赖所有基础服务的聚合服务
    # 注意：这需要在运行时动态构建，这里简化为依赖部分服务
    class Dep1:
        pass

    class Dep2:
        pass

    class Dep3:
        pass

    class Dep4:
        pass

    class Dep5:
        pass

    class AggregateService:
        def __init__(
            self,
            d1: Dep1,
            d2: Dep2,
            d3: Dep3,
            d4: Dep4,
            d5: Dep5,
        ) -> None:
            self.deps = [d1, d2, d3, d4, d5]

    container.register(Dep1, lifetime=Lifetime.SINGLETON)
    container.register(Dep2, lifetime=Lifetime.SINGLETON)
    container.register(Dep3, lifetime=Lifetime.SINGLETON)
    container.register(Dep4, lifetime=Lifetime.SINGLETON)
    container.register(Dep5, lifetime=Lifetime.SINGLETON)
    container.register(AggregateService, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(AggregateService))
    assert result is not None


# ============================================================================
# 依赖检测缓存性能测试
# ============================================================================


def test_repeated_resolution_with_cache_performance(benchmark, container):
    """测试重复解析时依赖检测缓存的效果."""

    class ServiceA:
        pass

    class ServiceB:
        def __init__(self, a: ServiceA) -> None:
            self.a = a

    class ServiceC:
        def __init__(self, b: ServiceB) -> None:
            self.b = b

    container.register(ServiceA, lifetime=Lifetime.SINGLETON)
    container.register(ServiceB, lifetime=Lifetime.SINGLETON)
    container.register(ServiceC, lifetime=Lifetime.TRANSIENT)

    # 预热依赖缓存
    container.resolve(ServiceC)

    # 测试有缓存时的性能
    result = benchmark(lambda: container.resolve(ServiceC))
    assert result is not None


# ============================================================================
# 循环依赖检测基准测试
# ============================================================================


def test_no_circular_dependency_baseline(benchmark, container):
    """建立无循环依赖的性能基准."""

    class ServiceA:
        pass

    class ServiceB:
        def __init__(self, a: ServiceA) -> None:
            self.a = a

    container.register(ServiceA, lifetime=Lifetime.SINGLETON)
    container.register(ServiceB, lifetime=Lifetime.TRANSIENT)

    # 基准：正常依赖解析应该很快
    result = benchmark(lambda: container.resolve(ServiceB))
    assert result is not None


def test_with_circular_check_overhead_baseline(benchmark, container):
    """测试循环检测的性能开销基准."""

    class Service:
        pass

    container.register(Service, lifetime=Lifetime.SINGLETON)

    # 即使是简单服务也会经过循环检测
    result = benchmark(lambda: container.resolve(Service))
    assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
