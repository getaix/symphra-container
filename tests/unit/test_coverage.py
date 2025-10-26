"""覆盖率补充测试.

用于增加代码覆盖率的补充测试.
"""

import pytest

from symphra_container import (
    Container,
    Lifetime,
)


class TestContainerRegistration:
    """容器注册额外测试."""

    def test_register_with_override_false_raises_error(self, container) -> None:
        """测试重复注册而不覆盖会抛出异常."""

        class Service:
            pass

        container.register(Service)
        with pytest.raises(Exception):
            container.register(Service, override=False)

    def test_register_factory_with_service_type(self, container) -> None:
        """测试使用 service_type 注册工厂."""

        class Service:
            pass

        def factory():
            return Service()

        container.register_factory("service", factory, service_type=Service)
        service = container.resolve("service")
        assert isinstance(service, Service)

    def test_register_factory_without_service_type(self, container) -> None:
        """测试不提供 service_type 的工厂注册."""

        def factory():
            return {"value": 42}

        container.register_factory("data", factory)
        result = container.resolve("data")
        assert result == {"value": 42}


class TestContainerResolution:
    """容器解析额外测试."""

    def test_resolve_with_factory_lifetime(self, container) -> None:
        """测试使用 FACTORY 生命周期解析."""
        counter = 0

        def factory():
            nonlocal counter
            counter += 1
            return counter

        container.register_factory("counter", factory, lifetime=Lifetime.FACTORY)
        result1 = container.resolve("counter")
        result2 = container.resolve("counter")

        assert result1 == 1
        assert result2 == 2

    def test_resolve_with_string_key(self, container) -> None:
        """测试使用字符串键解析."""

        class Service:
            pass

        container.register(Service, key="my_service")
        service = container.resolve("my_service")
        assert isinstance(service, Service)


class TestContainerInspection:
    """容器检查方法额外测试."""

    def test_get_registration_for_nonexistent_service(self, container) -> None:
        """测试获取不存在服务的注册."""
        result = container.get_registration("nonexistent")
        assert result is None

    def test_get_all_registrations_empty(self) -> None:
        """测试空容器的所有注册."""
        container = Container()
        registrations = container.get_all_registrations()
        assert len(registrations) == 0

    def test_get_all_registrations_multiple(self, container) -> None:
        """测试多个注册的获取."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        container.register(ServiceA)
        container.register(ServiceB)
        container.register(ServiceC)

        registrations = container.get_all_registrations()
        assert len(registrations) == 3


class TestContainerErrors:
    """容器错误处理额外测试."""

    def test_resolve_nonexistent_returns_correct_error(self, container) -> None:
        """测试解析不存在的服务返回正确错误."""
        from symphra_container import ServiceNotFoundError

        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.resolve("missing")

        assert "missing" in str(exc_info.value)

    def test_invalid_interceptor_type(self, container) -> None:
        """测试无效的拦截器类型."""

        def dummy_interceptor(key, registration) -> bool:
            return True

        with pytest.raises(ValueError):
            container.add_interceptor("invalid_type", dummy_interceptor)

    def test_container_initialization_with_config(self) -> None:
        """测试容器初始化配置."""
        container = Container(enable_auto_wiring=False, strict_mode=False)
        assert container.enable_auto_wiring is False
        assert container.strict_mode is False

    def test_container_initialization_invalid_config(self) -> None:
        """测试无效的容器配置."""
        from symphra_container import InvalidConfigurationError

        with pytest.raises(InvalidConfigurationError):
            Container(enable_auto_wiring=True, strict_mode=True)


class TestContainerScopes:
    """容器作用域额外测试."""

    def test_scope_context_manager(self, container) -> None:
        """测试作用域上下文管理器."""

        class Service:
            pass

        container.register(Service, lifetime=Lifetime.SCOPED)

        with container.create_scope():
            service = container.resolve(Service)
            assert isinstance(service, Service)

    def test_multiple_sequential_scopes(self, container) -> None:
        """测试多个顺序作用域."""

        class Service:
            pass

        container.register(Service, lifetime=Lifetime.SCOPED)

        services = []
        for _ in range(3):
            with container.create_scope():
                service = container.resolve(Service)
                services.append(service)

        # 不同作用域中的服务应该不同
        assert services[0] is not services[1]
        assert services[1] is not services[2]


class TestContainerChainingAPI:
    """容器链式 API 额外测试."""

    def test_chained_registration_multiple(self, container) -> None:
        """测试多个链式注册."""

        class Service1:
            pass

        class Service2:
            pass

        class Service3:
            pass

        # 测试链式调用
        result = container.register(Service1).register(Service2).register(Service3)

        # 应该返回容器实例
        assert result is container

        # 所有服务应该被注册
        assert container.is_registered(Service1)
        assert container.is_registered(Service2)
        assert container.is_registered(Service3)

    def test_chained_instance_registration(self, container) -> None:
        """测试链式实例注册."""
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2"}

        result = container.register_instance("obj1", obj1).register_instance("obj2", obj2)

        assert result is container
        assert container.resolve("obj1") is obj1
        assert container.resolve("obj2") is obj2


class TestServiceRegistrationInfo:
    """服务注册信息测试."""

    def test_service_registration_repr(self, container) -> None:
        """测试服务注册的字符串表示."""
        from symphra_container.container import ServiceRegistration

        class MyService:
            pass

        reg = ServiceRegistration(
            key=MyService,
            service_type=MyService,
            lifetime=Lifetime.SINGLETON,
        )

        repr_str = repr(reg)
        assert "MyService" in repr_str
        assert "SINGLETON" in repr_str


class TestContainerDisposal:
    """容器释放额外测试."""

    def test_container_context_manager(self) -> None:
        """测试容器上下文管理器."""

        class Service:
            pass

        with Container() as container:
            container.register(Service)
            service = container.resolve(Service)
            assert isinstance(service, Service)

        # 退出后容器应该被释放
        assert len(container._registrations) == 0

    def test_dispose_clears_all_state(self, container) -> None:
        """测试 dispose 清空所有状态."""

        class Service:
            pass

        container.register(Service, lifetime=Lifetime.SINGLETON)
        container.resolve(Service)

        container.dispose()

        # 所有状态应该被清空
        assert len(container._registrations) == 0
        assert len(container._interceptors) == 0
        assert container._circular_detector.current_depth == 0
