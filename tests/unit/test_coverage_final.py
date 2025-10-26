"""最后的覆盖率提升测试.

专注于覆盖尚未被测试的代码路径.
"""

from typing import Never

import pytest

from symphra_container import (
    Container,
    Lifetime,
    ServiceNotFoundError,
    ServiceRegistration,
)


class TestRegistrationInfo:
    """服务注册信息的完整测试."""

    def test_registration_with_all_fields(self) -> None:
        """测试所有字段的注册."""

        class Service:
            pass

        reg = ServiceRegistration(
            key="test_key",
            service_type=Service,
            factory=lambda: Service(),
            lifetime=Lifetime.SINGLETON,
            override=True,
        )

        assert reg.key == "test_key"
        assert reg.service_type is Service
        assert reg.lifetime == Lifetime.SINGLETON
        assert reg.override is True


class TestContainerAPICompleteness:
    """容器 API 完整性测试."""

    def test_register_returns_container_for_chaining(self, container) -> None:
        """测试 register 返回容器以支持链式调用."""

        class Service:
            pass

        result = container.register(Service)
        assert result is container

    def test_register_instance_returns_container(self, container) -> None:
        """测试 register_instance 返回容器."""
        result = container.register_instance("key", "value")
        assert result is container

    def test_register_factory_returns_container(self, container) -> None:
        """测试 register_factory 返回容器."""
        result = container.register_factory("key", lambda: "value")
        assert result is container

    def test_add_interceptor_returns_container(self, container) -> None:
        """测试 add_interceptor 返回容器."""

        def dummy(key, reg) -> bool:
            return True

        result = container.add_interceptor("before", dummy)
        assert result is container

    def test_is_registered_for_type_key(self, container) -> None:
        """测试类型键的 is_registered."""

        class Service:
            pass

        assert not container.is_registered(Service)
        container.register(Service)
        assert container.is_registered(Service)

    def test_is_registered_for_string_key(self, container) -> None:
        """测试字符串键的 is_registered."""
        container.register_instance("myservice", "value")
        assert container.is_registered("myservice")

    def test_get_registration_returns_copy(self, container) -> None:
        """测试 get_all_registrations 返回副本."""

        class Service:
            pass

        container.register(Service)
        registrations1 = container.get_all_registrations()
        registrations2 = container.get_all_registrations()

        # 应该是不同的对象(副本)
        assert registrations1 is not registrations2
        # 但内容应该相同
        assert registrations1.keys() == registrations2.keys()


class TestContainerLifecycleCompleteness:
    """容器生命周期的完整测试."""

    def test_transient_service_new_instance(self, container) -> None:
        """测试瞬时服务总是创建新实例."""

        class Counter:
            instances = 0

            def __init__(self) -> None:
                Counter.instances += 1
                self.id = Counter.instances

        container.register(Counter, lifetime=Lifetime.TRANSIENT)

        c1 = container.resolve(Counter)
        c2 = container.resolve(Counter)
        c3 = container.resolve(Counter)

        assert c1.id == 1
        assert c2.id == 2
        assert c3.id == 3
        assert c1 is not c2
        assert c2 is not c3

    def test_singleton_reuse(self, container) -> None:
        """测试单例的重用."""
        instances_created = 0

        class Service:
            def __init__(self) -> None:
                nonlocal instances_created
                instances_created += 1

        container.register(Service, lifetime=Lifetime.SINGLETON)

        s1 = container.resolve(Service)
        s2 = container.resolve(Service)
        s3 = container.resolve(Service)

        assert s1 is s2 is s3
        assert instances_created == 1

    def test_factory_creates_each_time(self, container) -> None:
        """测试工厂每次创建实例."""
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        container.register_factory("service", factory, lifetime=Lifetime.FACTORY)

        r1 = container.resolve("service")
        r2 = container.resolve("service")
        r3 = container.resolve("service")

        assert r1 == "instance_1"
        assert r2 == "instance_2"
        assert r3 == "instance_3"


class TestExceptionMessages:
    """异常消息的完整测试."""

    def test_service_not_found_includes_key(self, container) -> None:
        """测试 ServiceNotFoundError 包含服务键."""
        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.resolve("missing_service")

        error_msg = str(exc_info.value)
        assert "missing_service" in error_msg

    def test_service_not_found_with_type_key(self, container) -> None:
        """测试使用类型键的 ServiceNotFoundError."""

        class MissingService:
            pass

        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.resolve(MissingService)

        error_msg = str(exc_info.value)
        assert "MissingService" in error_msg


class TestDependencyInjectionPaths:
    """依赖注入的各种路径测试."""

    def test_deep_dependency_chain(self, container) -> None:
        """测试深层依赖链(5 层)."""

        class Level5:
            pass

        class Level4:
            def __init__(self, l5: Level5) -> None:
                self.l5 = l5

        class Level3:
            def __init__(self, l4: Level4) -> None:
                self.l4 = l4

        class Level2:
            def __init__(self, l3: Level3) -> None:
                self.l3 = l3

        class Level1:
            def __init__(self, l2: Level2) -> None:
                self.l2 = l2

        container.register(Level5)
        container.register(Level4)
        container.register(Level3)
        container.register(Level2)
        container.register(Level1)

        l1 = container.resolve(Level1)

        assert isinstance(l1, Level1)
        assert isinstance(l1.l2, Level2)
        assert isinstance(l1.l2.l3, Level3)
        assert isinstance(l1.l2.l3.l4, Level4)
        assert isinstance(l1.l2.l3.l4.l5, Level5)

    def test_multiple_service_registration_different_keys(self, container) -> None:
        """测试同一类型的多个键注册."""

        class Config:
            def __init__(self, name: str) -> None:
                self.name = name

        config_dev = Config("dev")
        config_prod = Config("prod")

        container.register_instance("config.dev", config_dev)
        container.register_instance("config.prod", config_prod)

        assert container.resolve("config.dev") is config_dev
        assert container.resolve("config.prod") is config_prod
        assert config_dev is not config_prod


class TestContainerErrorHandling:
    """容器的错误处理完整性."""

    def test_invalid_configuration_error(self) -> None:
        """测试无效配置错误."""
        from symphra_container import InvalidConfigurationError

        with pytest.raises(InvalidConfigurationError):
            Container(enable_auto_wiring=True, strict_mode=True)

    def test_resolution_error_with_cause(self, container) -> None:
        """测试带原因的解析错误."""
        from symphra_container import ResolutionError

        def bad_factory() -> Never:
            msg = "Factory failed!"
            raise ValueError(msg)

        container.register_factory("bad", bad_factory)

        with pytest.raises(ResolutionError):
            container.resolve("bad")

    def test_registration_error_on_duplicate(self, container) -> None:
        """测试重复注册错误."""
        from symphra_container import RegistrationError

        class Service:
            pass

        container.register(Service)

        with pytest.raises(RegistrationError):
            container.register(Service, override=False)


class TestScopeManagement:
    """作用域管理的完整测试."""

    def test_scope_context_manager_cleanup(self, container) -> None:
        """测试作用域上下文管理器的清理."""

        class Disposable:
            def __init__(self) -> None:
                self.disposed = False

            def dispose(self) -> None:
                self.disposed = True

        disposable_instance = Disposable()
        container.register_instance("disposable", disposable_instance)

        with container.create_scope():
            disposable = container.resolve("disposable")
            # 在作用域内,实例应该存在
            assert isinstance(disposable, Disposable)
            assert disposable is disposable_instance

    def test_scope_isolation(self, container) -> None:
        """测试作用域隔离."""

        class Counter:
            counter = 0

            def __init__(self) -> None:
                Counter.counter += 1
                self.id = Counter.counter

        container.register(Counter, lifetime=Lifetime.SCOPED)

        counters = []

        # 第一个作用域
        with container.create_scope():
            c1 = container.resolve(Counter)
            counters.append(c1)

        # 第二个作用域
        with container.create_scope():
            c2 = container.resolve(Counter)
            counters.append(c2)

        # 应该是不同的实例
        assert counters[0] is not counters[1]
        assert counters[0].id == 1
        assert counters[1].id == 2


class TestContainerContextManager:
    """容器上下文管理器的测试."""

    def test_context_manager_disposes_resources(self) -> None:
        """测试上下文管理器释放资源."""
        disposed = False

        class Service:
            def dispose(self) -> None:
                nonlocal disposed
                disposed = True

        with Container() as container:
            container.register_instance("service", Service())
            assert not disposed

        # 离开上下文后应该释放资源
        assert disposed

    def test_container_operations_in_context(self) -> None:
        """测试在上下文中的容器操作."""

        class Service:
            pass

        with Container() as container:
            container.register(Service)
            service = container.resolve(Service)
            assert isinstance(service, Service)
