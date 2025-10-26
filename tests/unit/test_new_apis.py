"""测试新增的API方法."""

import pytest

from symphra_container import Container, Lifetime
from symphra_container.exceptions import ServiceNotFoundError


class SimpleService:
    """简单服务."""


class DatabaseService:
    """数据库服务."""


class CacheService:
    """缓存服务."""


class TestTryResolve:
    """测试 try_resolve 方法."""

    def test_try_resolve_existing_service(self) -> None:
        """测试解析已存在的服务."""
        container = Container()
        container.register(SimpleService)

        service = container.try_resolve(SimpleService)
        assert service is not None
        assert isinstance(service, SimpleService)

    def test_try_resolve_nonexistent_service_returns_none(self) -> None:
        """测试解析不存在的服务返回 None."""
        container = Container()

        result = container.try_resolve(SimpleService)
        assert result is None

    def test_try_resolve_with_custom_default(self) -> None:
        """测试使用自定义默认值."""
        container = Container()
        default_service = SimpleService()

        result = container.try_resolve(SimpleService, default=default_service)
        assert result is default_service


class TestUnregister:
    """测试 unregister 方法."""

    def test_unregister_existing_service(self) -> None:
        """测试取消注册已存在的服务."""
        container = Container()
        container.register(SimpleService)
        assert container.is_registered(SimpleService)

        container.unregister(SimpleService)
        assert not container.is_registered(SimpleService)

    def test_unregister_nonexistent_service_silent(self) -> None:
        """测试取消注册不存在的服务不抛出异常."""
        container = Container()
        # 不应该抛出异常
        container.unregister(SimpleService)

    def test_unregister_singleton_removes_instance(self) -> None:
        """测试取消注册单例服务会移除实例."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        service1 = container.resolve(SimpleService)

        container.unregister(SimpleService)
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        service2 = container.resolve(SimpleService)

        # 应该是不同的实例
        assert service1 is not service2


class TestClear:
    """测试 clear 方法."""

    def test_clear_all_services(self) -> None:
        """测试清除所有服务."""
        container = Container()
        container.register(SimpleService)
        container.register(DatabaseService)
        container.register(CacheService)

        container.clear()
        assert not container.is_registered(SimpleService)
        assert not container.is_registered(DatabaseService)
        assert not container.is_registered(CacheService)

    def test_clear_singleton_only(self) -> None:
        """测试只清除单例服务."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        container.register(DatabaseService, lifetime=Lifetime.TRANSIENT)

        container.clear(lifetime=Lifetime.SINGLETON)
        assert not container.is_registered(SimpleService)
        assert container.is_registered(DatabaseService)

    def test_clear_transient_only(self) -> None:
        """测试只清除瞬态服务."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        container.register(DatabaseService, lifetime=Lifetime.TRANSIENT)

        container.clear(lifetime=Lifetime.TRANSIENT)
        assert container.is_registered(SimpleService)
        assert not container.is_registered(DatabaseService)


class TestReplace:
    """测试 replace 方法."""

    def test_replace_existing_service(self) -> None:
        """测试替换已存在的服务."""
        container = Container()
        container.register(SimpleService)

        # 解析旧服务
        service1 = container.resolve(SimpleService)
        assert isinstance(service1, SimpleService)

        # 替换为新类型
        container.replace(SimpleService, DatabaseService)

        # 解析新服务
        service2 = container.resolve(SimpleService)
        assert isinstance(service2, DatabaseService)

    def test_replace_nonexistent_service_raises(self) -> None:
        """测试替换不存在的服务抛出异常."""
        container = Container()

        with pytest.raises(ServiceNotFoundError):
            container.replace(SimpleService, DatabaseService)

    def test_replace_preserves_lifetime(self) -> None:
        """测试替换保留生命周期."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)

        # 获取旧注册信息
        old_registration = container.get_registration(SimpleService)
        old_lifetime = old_registration.lifetime

        # 替换
        container.replace(SimpleService, DatabaseService)

        # 检查新注册信息
        new_registration = container.get_registration(SimpleService)
        assert new_registration.lifetime == old_lifetime


class TestHas:
    """测试 has 方法."""

    def test_has_registered_service(self) -> None:
        """测试 has 方法检查已注册的服务."""
        container = Container()
        container.register(SimpleService)

        assert container.has(SimpleService)

    def test_has_unregistered_service(self) -> None:
        """测试 has 方法检查未注册的服务."""
        container = Container()

        assert not container.has(SimpleService)

    def test_has_is_alias_of_is_registered(self) -> None:
        """测试 has 是 is_registered 的别名."""
        container = Container()
        container.register(SimpleService)

        assert container.has(SimpleService) == container.is_registered(SimpleService)


class TestAlias:
    """测试 alias 方法."""

    def test_create_alias(self) -> None:
        """测试创建别名."""
        container = Container()
        container.register(SimpleService)

        container.alias(SimpleService, "my_service")
        assert container.is_registered("my_service")

    def test_resolve_by_alias(self) -> None:
        """测试通过别名解析."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        container.alias(SimpleService, "my_service")

        service1 = container.resolve(SimpleService)
        service2 = container.resolve("my_service")

        # 应该是同一个实例
        assert service1 is service2

    def test_alias_nonexistent_service_raises(self) -> None:
        """测试为不存在的服务创建别名抛出异常."""
        container = Container()

        with pytest.raises(ServiceNotFoundError):
            container.alias(SimpleService, "my_service")


class TestWarmup:
    """测试 warmup 方法."""

    def test_warmup_specific_services(self) -> None:
        """测试预热指定服务."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        container.register(DatabaseService, lifetime=Lifetime.SINGLETON)

        # 预热
        container.warmup(SimpleService, DatabaseService)

        # 应该已经创建实例
        service1a = container.resolve(SimpleService)
        service1b = container.resolve(SimpleService)
        assert service1a is service1b

    def test_warmup_all_singletons(self) -> None:
        """测试预热所有单例."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        container.register(DatabaseService, lifetime=Lifetime.SINGLETON)
        container.register(CacheService, lifetime=Lifetime.TRANSIENT)

        # 预热所有单例
        container.warmup()

        # 单例应该已创建
        assert container.resolve(SimpleService) is not None
        assert container.resolve(DatabaseService) is not None

    def test_warmup_ignores_errors(self) -> None:
        """测试预热时忽略错误."""
        container = Container()

        class FailingService:
            def __init__(self) -> None:
                msg = "fail"
                raise ValueError(msg)

        container.register(FailingService, lifetime=Lifetime.SINGLETON)
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)

        # 不应该抛出异常
        container.warmup()

        # 正常服务应该可以解析
        assert container.resolve(SimpleService) is not None


class TestShorthandSyntax:
    """测试简写语法."""

    def test_getitem_resolve(self) -> None:
        """测试 __getitem__ 解析服务."""
        container = Container()
        container.register(SimpleService)

        service = container[SimpleService]
        assert isinstance(service, SimpleService)

    def test_setitem_register(self) -> None:
        """测试 __setitem__ 注册服务."""
        container = Container()
        container[SimpleService] = SimpleService

        assert container.is_registered(SimpleService)
        service = container[SimpleService]
        assert isinstance(service, SimpleService)

    def test_setitem_register_instance(self) -> None:
        """测试 __setitem__ 注册实例."""
        container = Container()
        instance = SimpleService()

        container["my_service"] = instance
        resolved = container["my_service"]
        assert resolved is instance

    def test_getitem_nonexistent_raises(self) -> None:
        """测试 __getitem__ 不存在的服务抛出异常."""
        container = Container()

        with pytest.raises(ServiceNotFoundError):
            _ = container[SimpleService]


class TestChainedNewAPIs:
    """测试新API的链式调用."""

    def test_register_then_alias(self) -> None:
        """测试注册后创建别名."""
        container = Container()
        container.register(SimpleService).alias(SimpleService, "simple")

        assert container.has("simple")
        assert isinstance(container["simple"], SimpleService)

    def test_replace_then_warmup(self) -> None:
        """测试替换后预热."""
        container = Container()
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        container.replace(SimpleService, DatabaseService)
        container.warmup(SimpleService)

        service = container[SimpleService]
        assert isinstance(service, DatabaseService)
