"""装饰器系统性能测试.

测试装饰器的性能表现:
- @injectable, @singleton, @transient 装饰器
- @factory 装饰器
- @auto_register 装饰器
- 装饰器元数据提取性能
"""

import pytest

from symphra_container import (
    Container,
    Lifetime,
    auto_register,
    factory,
    get_service_metadata,
    injectable,
    is_injectable,
    scoped,
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


# ============================================================================
# 装饰器应用性能测试
# ============================================================================


def test_singleton_decorator_performance(benchmark):
    """测试 @singleton 装饰器的应用性能."""

    def apply_decorator():
        @singleton
        class Service:
            pass

        return Service

    result = benchmark(apply_decorator)
    assert is_injectable(result)


def test_transient_decorator_performance(benchmark):
    """测试 @transient 装饰器的应用性能."""

    def apply_decorator():
        @transient
        class Service:
            pass

        return Service

    result = benchmark(apply_decorator)
    assert is_injectable(result)


def test_scoped_decorator_performance(benchmark):
    """测试 @scoped 装饰器的应用性能."""

    def apply_decorator():
        @scoped
        class Service:
            pass

        return Service

    result = benchmark(apply_decorator)
    assert is_injectable(result)


def test_injectable_decorator_performance(benchmark):
    """测试 @injectable 装饰器的应用性能."""

    def apply_decorator():
        @injectable
        class Service:
            pass

        return Service

    result = benchmark(apply_decorator)
    assert is_injectable(result)


def test_factory_decorator_performance(benchmark):
    """测试 @factory 装饰器的应用性能."""

    def apply_decorator():
        @factory
        def create_service():
            return {"key": "value"}

        return create_service

    result = benchmark(apply_decorator)
    assert callable(result)


# ============================================================================
# 装饰器注册性能测试
# ============================================================================


def test_register_decorated_singleton_performance(benchmark, container):
    """测试注册被 @singleton 装饰的类的性能."""

    @singleton
    class Service:
        pass

    benchmark(lambda: container.register(Service))
    # 验证注册成功
    assert Service in container._registrations


def test_register_decorated_transient_performance(benchmark, container):
    """测试注册被 @transient 装饰的类的性能."""

    @transient
    class Service:
        pass

    def register_service():
        c = Container()
        c.register(Service)
        return c

    result = benchmark(register_service)
    assert Service in result._registrations


def test_register_multiple_decorated_services_performance(benchmark):
    """测试批量注册装饰类的性能."""

    @singleton
    class Service1:
        pass

    @transient
    class Service2:
        pass

    @scoped
    class Service3:
        pass

    @injectable
    class Service4:
        pass

    def register_all():
        c = Container()
        c.register(Service1)
        c.register(Service2)
        c.register(Service3)
        c.register(Service4)
        return c

    result = benchmark(register_all)
    assert len(result._registrations) >= 4


# ============================================================================
# 元数据提取性能测试
# ============================================================================


def test_get_service_metadata_performance(benchmark):
    """测试获取服务元数据的性能."""

    @singleton
    class Service:
        pass

    result = benchmark(lambda: get_service_metadata(Service))
    assert result is not None
    assert result.lifetime == Lifetime.SINGLETON


def test_is_injectable_check_performance(benchmark):
    """测试 is_injectable 检查的性能."""

    @injectable
    class Service:
        pass

    result = benchmark(lambda: is_injectable(Service))
    assert result is True


def test_metadata_extraction_for_non_decorated_class_performance(benchmark):
    """测试非装饰类的元数据提取性能."""

    class PlainService:
        pass

    result = benchmark(lambda: get_service_metadata(PlainService))
    assert result is None


# ============================================================================
# @auto_register 装饰器性能测试
# ============================================================================


def test_auto_register_decorator_performance(benchmark, container):
    """测试 @auto_register 装饰器的性能."""

    def apply_and_register():
        c = Container()

        @auto_register(c)
        class Service:
            pass

        return c, Service

    result_container, service_class = benchmark(apply_and_register)
    assert service_class in result_container._registrations


def test_auto_register_with_lifetime_performance(benchmark):
    """测试带生命周期参数的 @auto_register 性能."""

    def apply_and_register():
        c = Container()

        @auto_register(c, lifetime=Lifetime.SINGLETON)
        class Service:
            pass

        return c, Service

    result_container, service_class = benchmark(apply_and_register)
    assert service_class in result_container._registrations


def test_auto_register_with_key_performance(benchmark):
    """测试带键参数的 @auto_register 性能."""

    def apply_and_register():
        c = Container()

        @auto_register(c, key="my_service")
        class Service:
            pass

        return c, Service

    result_container, _ = benchmark(apply_and_register)
    assert "my_service" in result_container._registrations


# ============================================================================
# 装饰器解析性能测试
# ============================================================================


def test_resolve_decorated_singleton_performance(benchmark):
    """测试解析被 @singleton 装饰的服务的性能."""

    @singleton
    class Service:
        pass

    container = Container()
    container.register(Service)

    # 预热
    container.resolve(Service)

    result = benchmark(lambda: container.resolve(Service))
    assert result is not None


def test_resolve_decorated_transient_performance(benchmark):
    """测试解析被 @transient 装饰的服务的性能."""

    @transient
    class Service:
        pass

    container = Container()
    container.register(Service)

    result = benchmark(lambda: container.resolve(Service))
    assert result is not None


def test_resolve_decorated_with_dependencies_performance(benchmark):
    """测试解析带依赖的装饰服务的性能."""

    @singleton
    class Database:
        pass

    @singleton
    class Cache:
        pass

    @transient
    class UserService:
        def __init__(self, db: Database, cache: Cache) -> None:
            self.db = db
            self.cache = cache

    container = Container()
    container.register(Database)
    container.register(Cache)
    container.register(UserService)

    result = benchmark(lambda: container.resolve(UserService))
    assert result is not None
    assert hasattr(result, "db")
    assert hasattr(result, "cache")


# ============================================================================
# 工厂装饰器性能测试
# ============================================================================


def test_factory_decorator_registration_performance(benchmark):
    """测试注册工厂函数的性能."""

    @factory
    def create_config():
        return {"app_name": "MyApp", "version": "1.0"}

    def register_factory():
        c = Container()
        c.register_factory("config", create_config)
        return c

    result = benchmark(register_factory)
    assert "config" in result._registrations


def test_factory_decorator_resolution_performance(benchmark):
    """测试解析工厂函数创建的服务的性能."""

    @factory
    def create_service():
        return {"data": [1, 2, 3, 4, 5]}

    container = Container()
    container.register_factory("service", create_service, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve("service"))
    assert result is not None


def test_factory_with_dependencies_performance(benchmark):
    """测试带依赖的工厂函数性能."""

    class Config:
        def __init__(self) -> None:
            self.value = "config"

    @factory
    def create_service(config: Config):
        return {"config": config.value}

    container = Container()
    container.register(Config, lifetime=Lifetime.SINGLETON)
    container.register_factory("service", create_service, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve("service"))
    assert result is not None


# ============================================================================
# 混合装饰器场景性能测试
# ============================================================================


def test_mixed_decorators_registration_performance(benchmark):
    """测试混合使用多种装饰器的注册性能."""

    @singleton
    class SingletonService:
        pass

    @transient
    class TransientService:
        pass

    @scoped
    class ScopedService:
        pass

    @injectable
    class InjectableService:
        pass

    @factory
    def create_data():
        return [1, 2, 3]

    def register_all():
        c = Container()
        c.register(SingletonService)
        c.register(TransientService)
        c.register(ScopedService)
        c.register(InjectableService)
        c.register_factory("data", create_data)
        return c

    result = benchmark(register_all)
    assert len(result._registrations) >= 5


def test_mixed_decorators_resolution_performance(benchmark):
    """测试混合装饰器服务的解析性能."""

    @singleton
    class SingletonService:
        pass

    @transient
    class TransientService:
        def __init__(self, singleton: SingletonService) -> None:
            self.singleton = singleton

    container = Container()
    container.register(SingletonService)
    container.register(TransientService)

    result = benchmark(lambda: container.resolve(TransientService))
    assert result is not None
    assert hasattr(result, "singleton")


# ============================================================================
# 装饰器链性能测试
# ============================================================================


def test_decorator_chain_performance(benchmark):
    """测试多个装饰器链的性能."""

    def apply_decorators():
        @singleton
        @injectable
        class Service:
            pass

        return Service

    result = benchmark(apply_decorators)
    assert is_injectable(result)


# ============================================================================
# 大规模装饰器使用性能测试
# ============================================================================


def test_large_scale_decorated_services_performance(benchmark):
    """测试大规模使用装饰器的性能."""

    def register_many():
        c = Container()

        # 创建并注册50个装饰服务
        for i in range(50):

            @singleton
            class Service:
                pass

            c.register(Service, key=f"service_{i}")

        return c

    result = benchmark(register_many)
    assert len(result._registrations) >= 50


def test_resolve_many_decorated_services_performance(benchmark):
    """测试解析大量装饰服务的性能."""
    container = Container()
    services = []

    # 注册50个装饰服务
    for i in range(50):

        @singleton
        class Service:
            pass

        key = f"service_{i}"
        container.register(Service, key=key)
        services.append(key)

    # 预热
    for key in services:
        container.resolve(key)

    # 测试解析
    def resolve_all():
        return [container.resolve(key) for key in services]

    result = benchmark(resolve_all)
    assert len(result) == 50


# ============================================================================
# 装饰器性能基准测试
# ============================================================================


def test_decorator_overhead_baseline(benchmark):
    """测试装饰器本身的性能开销."""

    def without_decorator():
        class Service:
            pass

        return Service

    def with_decorator():
        @singleton
        class Service:
            pass

        return Service

    # 测试带装饰器的版本
    result = benchmark(with_decorator)
    assert is_injectable(result)


def test_registration_overhead_comparison(benchmark):
    """对比装饰和非装饰类的注册性能."""

    @singleton
    class DecoratedService:
        pass

    class PlainService:
        pass

    def register_decorated():
        c = Container()
        c.register(DecoratedService)
        return c

    # 测试装饰类的注册
    result = benchmark(register_decorated)
    assert DecoratedService in result._registrations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
