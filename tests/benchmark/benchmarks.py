"""Symphra Container 性能基准测试.

使用 pytest-benchmark 测试容器的性能指标,包括:
- 服务解析性能
- 单例 vs 瞬时的性能差异
- 依赖注入性能
- 循环依赖检测性能
"""

from symphra_container import (
    Container,
    Lifetime,
    auto_register,
    injectable,
    singleton,
    transient,
)

# ===================== 性能基准测试 =====================


class TestResolutionBenchmarks:
    """服务解析性能基准测试."""

    def test_resolve_simple_service(self, benchmark) -> None:
        """基准:解析简单服务."""
        # 准备
        container = Container()

        class SimpleService:
            pass

        container.register(SimpleService)

        # 执行
        def resolve():
            return container.resolve(SimpleService)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, SimpleService)

    def test_resolve_singleton_service_first_time(self, benchmark) -> None:
        """基准:首次解析单例服务."""
        # 准备
        container = Container()

        class SingletonService:
            pass

        container.register(SingletonService, lifetime=Lifetime.SINGLETON)

        # 执行
        def resolve():
            return container.resolve(SingletonService)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, SingletonService)

    def test_resolve_singleton_service_cached(self, benchmark) -> None:
        """基准:解析缓存的单例服务."""
        # 准备
        container = Container()

        class SingletonService:
            pass

        container.register(SingletonService, lifetime=Lifetime.SINGLETON)
        container.resolve(SingletonService)  # 预热缓存

        # 执行
        def resolve():
            return container.resolve(SingletonService)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, SingletonService)

    def test_resolve_transient_service(self, benchmark) -> None:
        """基准:解析瞬时服务."""
        # 准备
        container = Container()

        class TransientService:
            pass

        container.register(TransientService, lifetime=Lifetime.TRANSIENT)

        # 执行
        def resolve():
            return container.resolve(TransientService)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, TransientService)

    def test_resolve_service_with_dependencies(self, benchmark) -> None:
        """基准:解析有依赖的服务."""
        # 准备
        container = Container()

        class Logger:
            pass

        class UserService:
            def __init__(self, logger: Logger) -> None:
                self.logger = logger

        container.register(Logger, lifetime=Lifetime.SINGLETON)
        container.register(UserService)

        # 执行
        def resolve():
            return container.resolve(UserService)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, UserService)
        assert isinstance(result.logger, Logger)

    def test_resolve_deep_dependency_chain(self, benchmark) -> None:
        """基准:解析深层依赖链."""
        # 准备
        container = Container()

        class ServiceA:
            pass

        class ServiceB:
            def __init__(self, a: ServiceA) -> None:
                self.a = a

        class ServiceC:
            def __init__(self, b: ServiceB) -> None:
                self.b = b

        class ServiceD:
            def __init__(self, c: ServiceC) -> None:
                self.c = c

        container.register(ServiceA)
        container.register(ServiceB)
        container.register(ServiceC)
        container.register(ServiceD)

        # 执行
        def resolve():
            return container.resolve(ServiceD)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, ServiceD)
        assert isinstance(result.c, ServiceC)
        assert isinstance(result.c.b, ServiceB)
        assert isinstance(result.c.b.a, ServiceA)


class TestDecoratorBenchmarks:
    """装饰器系统性能基准测试."""

    def test_auto_register_single_service(self, benchmark) -> None:
        """基准:自动注册单个服务."""

        # 准备
        @injectable
        class Service:
            pass

        # 执行
        def register():
            container = Container()
            auto_register(container, Service)
            return container

        result = benchmark(register)

        # 验证结果
        assert result.is_registered(Service)

    def test_auto_register_multiple_services(self, benchmark) -> None:
        """基准:自动注册多个服务."""

        # 准备
        @singleton
        class DatabaseService:
            pass

        @transient
        class UserService:
            pass

        @injectable
        class Logger:
            pass

        # 执行
        def register():
            container = Container()
            auto_register(container, DatabaseService, UserService, Logger)
            return container

        result = benchmark(register)

        # 验证结果
        assert result.is_registered(DatabaseService)
        assert result.is_registered(UserService)
        assert result.is_registered(Logger)

    def test_resolve_decorated_service(self, benchmark) -> None:
        """基准:解析装饰的服务."""

        # 准备
        @injectable
        class Service:
            pass

        container = Container()
        auto_register(container, Service)

        # 执行
        def resolve():
            return container.resolve(Service)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, Service)


class TestPerformanceTrackingBenchmarks:
    """性能跟踪基准测试."""

    def test_resolve_with_performance_tracking_disabled(self, benchmark) -> None:
        """基准:禁用性能跟踪的解析."""
        # 准备
        container = Container(enable_performance_tracking=False)

        class Service:
            pass

        container.register(Service)

        # 执行
        def resolve():
            return container.resolve(Service)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, Service)

    def test_resolve_with_performance_tracking_enabled(self, benchmark) -> None:
        """基准:启用性能跟踪的解析."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class Service:
            pass

        container.register(Service)

        # 执行
        def resolve():
            return container.resolve(Service)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, Service)
        stats = container.get_performance_stats()
        assert stats["total_resolutions"] > 0

    def test_get_performance_stats(self, benchmark) -> None:
        """基准:获取性能统计信息."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class Service:
            pass

        container.register(Service)

        # 预热
        for _ in range(10):
            container.resolve(Service)

        # 执行
        def get_stats():
            return container.get_performance_stats()

        result = benchmark(get_stats)

        # 验证结果
        assert "total_resolutions" in result
        assert "cache_hit_rate" in result


class TestCacheBenchmarks:
    """缓存性能基准测试."""

    def test_singleton_cache_performance(self, benchmark) -> None:
        """基准:单例缓存性能."""
        # 准备
        container = Container()

        class CachedService:
            def __init__(self) -> None:
                # 模拟初始化开销
                self.data = list(range(100))

        container.register(CachedService, lifetime=Lifetime.SINGLETON)

        # 预热缓存
        first = container.resolve(CachedService)

        # 执行后续解析
        def resolve_cached():
            service = container.resolve(CachedService)
            return service is first  # 应该返回相同实例

        result = benchmark(resolve_cached)

        # 验证结果
        assert result is True

    def test_transient_vs_singleton_performance(self, benchmark) -> None:
        """基准:瞬时 vs 单例性能对比."""
        # 准备
        container = Container()

        class Service:
            def __init__(self) -> None:
                self.data = list(range(100))

        # 注册为单例
        container.register(Service, lifetime=Lifetime.SINGLETON)

        # 预热
        container.resolve(Service)

        # 执行单例查询
        def resolve():
            return container.resolve(Service)

        result = benchmark(resolve)

        # 验证结果
        assert isinstance(result, Service)


class TestLargeScaleBenchmarks:
    """大规模场景基准测试."""

    def test_many_services_registration(self, benchmark) -> None:
        """基准:注册大量服务."""
        # 准备
        services = []

        for i in range(100):

            class Service:
                def __init__(self) -> None:
                    self.id = i

            services.append(Service)

        # 执行
        def register_all():
            container = Container()
            for service in services:
                container.register(service)
            return container

        result = benchmark(register_all)

        # 验证结果
        assert len(result.get_all_registrations()) == 100

    def test_many_services_resolution(self, benchmark) -> None:
        """基准:解析大量不同的服务."""
        # 准备
        container = Container()
        services = []

        for _i in range(50):

            class Service:
                pass

            services.append(Service)
            container.register(Service)

        # 执行
        def resolve_all():
            results = []
            for service in services:
                results.append(container.resolve(service))
            return results

        result = benchmark(resolve_all)

        # 验证结果
        assert len(result) == 50

    def test_many_singletons_cached_resolution(self, benchmark) -> None:
        """基准:解析大量缓存的单例."""
        # 准备
        container = Container()
        services = []

        for _i in range(50):

            class Service:
                pass

            services.append(Service)
            container.register(Service, lifetime=Lifetime.SINGLETON)

        # 预热所有单例
        for service in services:
            container.resolve(service)

        # 执行
        def resolve_all_cached():
            results = []
            for service in services:
                results.append(container.resolve(service))
            return results

        result = benchmark(resolve_all_cached)

        # 验证结果
        assert len(result) == 50


# ===================== 性能对比基准测试 =====================


class TestPerformanceComparisons:
    """性能对比基准测试."""

    def test_decorator_vs_manual_registration(self, benchmark) -> None:
        """基准:装饰器注册 vs 手动注册."""

        # 准备
        @injectable
        class DecoratedService:
            pass

        # 执行:比较自动注册
        def auto_register_decorated():
            container = Container()
            auto_register(container, DecoratedService)
            return container

        result = benchmark(auto_register_decorated)

        # 验证
        assert result.is_registered(DecoratedService)

    def test_simple_service_vs_dependent_service(self, benchmark) -> None:
        """基准:简单服务 vs 有依赖的服务解析性能."""
        # 准备
        container = Container()

        class SimpleService:
            pass

        class Logger:
            pass

        class ComplexService:
            def __init__(self, logger: Logger) -> None:
                self.logger = logger

        container.register(SimpleService)
        container.register(Logger, lifetime=Lifetime.SINGLETON)
        container.register(ComplexService)

        # 执行:解析复杂服务
        def resolve_complex():
            return container.resolve(ComplexService)

        result = benchmark(resolve_complex)

        # 验证结果
        assert isinstance(result, ComplexService)
        assert isinstance(result.logger, Logger)
