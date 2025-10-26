"""性能测试 API 使用示例.

展示如何正确使用 symphra-container 的新 API 进行性能测试。
这是一个精简版的性能测试文件，展示正确的 API 调用方式。
"""

import pytest

from symphra_container import Container, Lifetime, injectable, singleton

# ============================================================================
# 正确的 API 使用示例
# ============================================================================


@pytest.fixture
def container():
    """创建容器实例."""
    return Container()


# ============================================================================
# 1. 基本服务注册 - 正确方式
# ============================================================================


def test_register_type_key_performance(benchmark, container):
    """测试使用类型作为键的注册性能 (正确方式)."""

    class SimpleService:
        pass

    # ✅ 正确: service_type 作为第一个参数，使用 override=True 允许重复注册
    def register():
        c = Container()
        for _ in range(10):
            c.register(SimpleService, lifetime=Lifetime.SINGLETON, override=True)
        return c

    result = benchmark(register)
    assert SimpleService in result._registrations


def test_register_string_key_performance(benchmark, container):
    """测试使用字符串键的注册性能 (正确方式)."""

    class SimpleService:
        pass

    # ✅ 正确: 使用 key 关键字参数
    def register():
        c = Container()
        for i in range(10):
            c.register(SimpleService, key=f"service_{i}", lifetime=Lifetime.SINGLETON)
        return c

    result = benchmark(register)
    assert "service_0" in result._registrations


# ============================================================================
# 2. 工厂注册 - 正确方式
# ============================================================================


def test_register_factory_performance(benchmark):
    """测试工厂函数注册性能 (正确方式)."""

    def create_config():
        return {"app_name": "MyApp"}

    # ✅ 正确: 使用 register_factory
    def register():
        c = Container()
        for i in range(10):
            c.register_factory(f"config_{i}", create_config, lifetime=Lifetime.SINGLETON)
        return c

    result = benchmark(register)
    assert "config_0" in result._registrations


# ============================================================================
# 3. 实例注册 - 正确方式
# ============================================================================


def test_register_instance_performance(benchmark):
    """测试实例注册性能 (正确方式)."""

    class Config:
        def __init__(self, value: str) -> None:
            self.value = value

    # ✅ 正确: 使用 register_instance
    def register():
        c = Container()
        for i in range(10):
            instance = Config(f"value_{i}")
            c.register_instance(f"config_{i}", instance)
        return c

    result = benchmark(register)
    assert "config_0" in result._registrations


# ============================================================================
# 4. 服务解析 - 正确方式
# ============================================================================


def test_resolve_singleton_performance(benchmark):
    """测试单例服务解析性能 (正确方式)."""

    @singleton
    class SingletonService:
        pass

    container = Container()
    # ✅ 正确: 直接使用类型作为键
    container.register(SingletonService)

    # 预热缓存
    container.resolve(SingletonService)

    # 测试缓存访问性能
    result = benchmark(lambda: container.resolve(SingletonService))
    assert result is not None


def test_resolve_with_string_key_performance(benchmark):
    """测试使用字符串键解析的性能 (正确方式)."""

    class Service:
        pass

    container = Container()
    # ✅ 正确: 使用 key 参数注册字符串键
    container.register(Service, key="my_service", lifetime=Lifetime.SINGLETON)

    # 预热
    container.resolve("my_service")

    # 测试
    result = benchmark(lambda: container.resolve("my_service"))
    assert result is not None


# ============================================================================
# 5. 依赖注入 - 正确方式
# ============================================================================


def test_resolve_with_dependencies_performance(benchmark):
    """测试依赖注入性能 (正确方式)."""

    @singleton
    class Database:
        pass

    @singleton
    class Cache:
        pass

    class UserService:
        def __init__(self, db: Database, cache: Cache) -> None:
            self.db = db
            self.cache = cache

    container = Container()
    # ✅ 正确: 按顺序注册依赖
    container.register(Database)
    container.register(Cache)
    container.register(UserService, lifetime=Lifetime.TRANSIENT)

    result = benchmark(lambda: container.resolve(UserService))
    assert result is not None
    assert hasattr(result, "db")
    assert hasattr(result, "cache")


# ============================================================================
# 6. 装饰器 - 正确方式
# ============================================================================


def test_decorated_service_performance(benchmark):
    """测试装饰服务性能 (正确方式)."""

    @singleton
    class DecoratedService:
        def __init__(self) -> None:
            self.value = 42

    container = Container()
    # ✅ 正确: 装饰器已设置元数据，直接注册
    container.register(DecoratedService)

    # 预热
    container.resolve(DecoratedService)

    result = benchmark(lambda: container.resolve(DecoratedService))
    assert result.value == 42


# ============================================================================
# 7. 作用域服务 - 正确方式
# ============================================================================


def test_scoped_service_performance(benchmark):
    """测试作用域服务性能 (正确方式)."""

    @injectable
    class ScopedService:
        pass

    container = Container()
    # ✅ 正确: 注册作用域服务
    container.register(ScopedService, lifetime=Lifetime.SCOPED)

    # ✅ 正确: 使用上下文管理器
    def resolve_scoped():
        with container.create_scope() as scope:
            return scope.resolve(ScopedService)

    # 预热
    resolve_scoped()

    result = benchmark(resolve_scoped)
    assert result is not None


# ============================================================================
# 8. 混合场景 - 正确方式
# ============================================================================


def test_mixed_registration_performance(benchmark):
    """测试混合注册场景的性能 (正确方式)."""

    @singleton
    class SingletonService:
        pass

    class TransientService:
        pass

    def create_factory_service():
        return {"data": "value"}

    class ConfigClass:
        pass

    config_instance = ConfigClass()

    def register_all():
        c = Container()
        # ✅ 类型键注册
        c.register(SingletonService)
        # ✅ 字符串键注册
        c.register(TransientService, key="transient", lifetime=Lifetime.TRANSIENT)
        # ✅ 工厂注册
        c.register_factory("factory_service", create_factory_service)
        # ✅ 实例注册
        c.register_instance("config", config_instance)
        return c

    result = benchmark(register_all)
    assert SingletonService in result._registrations
    assert "transient" in result._registrations
    assert "factory_service" in result._registrations
    assert "config" in result._registrations


# ============================================================================
# API 对比总结
# ============================================================================

"""
❌ 旧 API (错误):
    container.register(ServiceClass, key="key", lifetime=Lifetime.SINGLETON)
    container.register_factory("key", create_func, lifetime=Lifetime.SINGLETON)

✅ 新 API (正确):
    # 1. 类型键注册
    container.register(ServiceClass, lifetime=Lifetime.SINGLETON)

    # 2. 字符串键注册
    container.register(ServiceClass, key="my_key", lifetime=Lifetime.SINGLETON)

    # 3. 工厂注册
    container.register_factory("key", create_func, lifetime=Lifetime.SINGLETON)

    # 4. 实例注册
    container.register_instance("key", instance)

关键点:
1. register() 第一个参数永远是 service_type (类型)
2. 使用 key 关键字参数指定字符串键
3. 工厂使用 register_factory() 方法
4. 实例使用 register_instance() 方法
5. lifetime 始终作为关键字参数传递
"""

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
