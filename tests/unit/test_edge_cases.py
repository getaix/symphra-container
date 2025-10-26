"""边界情况和错误路径测试.

用于提高代码覆盖率的边界情况测试.
"""

import pytest

from symphra_container import (
    Lifetime,
    ServiceNotFoundError,
)


class TestContainerEdgeCases:
    """容器边界情况测试."""

    def test_register_instance_with_override_true(self, container) -> None:
        """测试使用 override=True 注册实例."""
        obj1 = {"value": 1}
        obj2 = {"value": 2}

        container.register_instance("data", obj1)
        container.register_instance("data", obj2, override=True)

        result = container.resolve("data")
        assert result is obj2

    def test_register_factory_with_override_true(self, container) -> None:
        """测试使用 override=True 注册工厂."""

        def factory1() -> str:
            return "value1"

        def factory2() -> str:
            return "value2"

        container.register_factory("service", factory1)
        container.register_factory("service", factory2, override=True)

        result = container.resolve("service")
        assert result == "value2"

    def test_resolve_with_no_registration(self, container) -> None:
        """测试解析未注册的服务."""
        with pytest.raises(ServiceNotFoundError):
            container.resolve("unknown_service")

    def test_container_with_chain_dependencies(self, container) -> None:
        """测试链式依赖."""

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

        service_d = container.resolve(ServiceD)

        assert isinstance(service_d, ServiceD)
        assert isinstance(service_d.c, ServiceC)
        assert isinstance(service_d.c.b, ServiceB)
        assert isinstance(service_d.c.b.a, ServiceA)

    def test_same_type_multiple_keys(self, container) -> None:
        """测试同一类型的多个键."""

        class Service:
            pass

        container.register(Service, key="service1")
        container.register(Service, key="service2", override=False)

        service1 = container.resolve("service1")
        service2 = container.resolve("service2")

        # 都是同一类型但不同实例(TRANSIENT)
        assert type(service1) == type(service2)
        assert service1 is not service2

    def test_factory_returning_none(self, container) -> None:
        """测试工厂返回 None."""

        def factory() -> None:
            return None

        container.register_factory("nullable", factory)
        result = container.resolve("nullable")

        assert result is None

    def test_singleton_lifetime_with_factory(self, container) -> None:
        """测试单例生命周期与工厂函数."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        container.register_factory("service", factory, lifetime=Lifetime.SINGLETON)

        result1 = container.resolve("service")
        result2 = container.resolve("service")

        assert result1 == {"count": 1}
        assert result2 == {"count": 1}
        assert call_count == 1

    def test_mixed_lifetime_registrations(self, container) -> None:
        """测试混合生命周期的注册."""

        class SingletonService:
            pass

        class TransientService:
            pass

        class ScopedService:
            pass

        container.register(SingletonService, lifetime=Lifetime.SINGLETON)
        container.register(TransientService, lifetime=Lifetime.TRANSIENT)
        container.register(ScopedService, lifetime=Lifetime.SCOPED)

        # 单例
        s1 = container.resolve(SingletonService)
        s2 = container.resolve(SingletonService)
        assert s1 is s2

        # 瞬时
        t1 = container.resolve(TransientService)
        t2 = container.resolve(TransientService)
        assert t1 is not t2

        # 作用域 - 需要在作用域内
        with container.create_scope():
            sc1 = container.resolve(ScopedService)
            sc2 = container.resolve(ScopedService)
            assert sc1 is sc2


class TestMultipleServices:
    """多个服务的注册和解析测试."""

    def test_large_number_of_registrations(self, container) -> None:
        """测试大量服务注册."""
        for i in range(100):
            class_name = f"Service{i}"
            locals()[class_name] = type(class_name, (), {})
            container.register(locals()[class_name], key=f"service_{i}")

        # 验证所有都被注册
        for i in range(100):
            assert container.is_registered(f"service_{i}")

    def test_resolve_all_registered_services(self, container) -> None:
        """测试解析所有已注册的服务."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        container.register(ServiceA)
        container.register(ServiceB)
        container.register(ServiceC)

        a = container.resolve(ServiceA)
        b = container.resolve(ServiceB)
        c = container.resolve(ServiceC)

        assert isinstance(a, ServiceA)
        assert isinstance(b, ServiceB)
        assert isinstance(c, ServiceC)


class TestContainerScopeEdgeCases:
    """作用域边界情况测试."""

    def test_scope_creation_and_disposal(self, container) -> None:
        """测试作用域创建和释放."""

        class Service:
            pass

        container.register(Service, lifetime=Lifetime.SCOPED)

        scope1 = container.create_scope()
        with scope1:
            service1 = container.resolve(Service)
            assert isinstance(service1, Service)

        scope2 = container.create_scope()
        with scope2:
            service2 = container.resolve(Service)
            assert isinstance(service2, Service)

        # 不同作用域中的服务应该不同
        assert service1 is not service2

    def test_multiple_services_in_scope(self, container) -> None:
        """测试作用域内的多个服务."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        container.register(ServiceA, lifetime=Lifetime.SCOPED)
        container.register(ServiceB, lifetime=Lifetime.SCOPED)

        with container.create_scope():
            a1 = container.resolve(ServiceA)
            b1 = container.resolve(ServiceB)
            a2 = container.resolve(ServiceA)
            b2 = container.resolve(ServiceB)

            # 同一作用域内应该是相同实例
            assert a1 is a2
            assert b1 is b2


class TestContainerErrorRecovery:
    """容器错误恢复测试."""

    def test_failed_resolution_does_not_corrupt_state(self, container) -> None:
        """测试失败的解析不会破坏容器状态."""

        class GoodService:
            pass

        class BadService:
            def __init__(self, nonexistent: "NonExistent") -> None:
                pass

        container.register(GoodService)
        container.register(BadService)

        # BadService 解析失败
        with pytest.raises(ServiceNotFoundError):
            container.resolve(BadService)

        # 但 GoodService 仍然可以解析
        good = container.resolve(GoodService)
        assert isinstance(good, GoodService)

    def test_multiple_failed_resolutions(self, container) -> None:
        """测试多个失败的解析."""

        class ServiceA:
            def __init__(self, missing: "Missing") -> None:
                pass

        class ServiceB:
            def __init__(self, also_missing: "AlsoMissing") -> None:
                pass

        container.register(ServiceA)
        container.register(ServiceB)

        # 两个都应该失败,但容器应该保持一致状态
        with pytest.raises(ServiceNotFoundError):
            container.resolve(ServiceA)

        with pytest.raises(ServiceNotFoundError):
            container.resolve(ServiceB)

        # 容器应该仍然可用
        assert container.is_registered(ServiceA)
        assert container.is_registered(ServiceB)
