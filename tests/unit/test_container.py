"""容器基础功能测试.

测试容器的核心功能:
- 服务注册
- 服务解析
- 生命周期管理
- 错误处理
"""

from typing import Never

import pytest

from symphra_container import (
    Container,
    Lifetime,
    RegistrationError,
    ResolutionError,
    ServiceNotFoundError,
)


class TestBasicRegistration:
    """基础注册功能测试."""

    def test_register_and_resolve_basic_service(self, container) -> None:
        """测试基础的服务注册和解析."""

        # 准备
        class UserService:
            pass

        # 执行
        container.register(UserService)
        service = container.resolve(UserService)

        # 断言
        assert isinstance(service, UserService)

    def test_register_with_string_key(self, container) -> None:
        """测试使用字符串键注册服务."""

        # 准备
        class UserService:
            pass

        # 执行
        container.register(UserService, key="user_service")
        service = container.resolve("user_service")

        # 断言
        assert isinstance(service, UserService)

    def test_register_instance(self, container) -> None:
        """测试注册单例实例."""
        # 准备
        config = {"debug": True}

        # 执行
        container.register_instance("config", config)
        resolved = container.resolve("config")

        # 断言
        assert resolved is config
        assert resolved == {"debug": True}

    def test_register_factory(self, container) -> None:
        """测试使用工厂函数注册服务."""

        # 准备
        class Database:
            def __init__(self) -> None:
                self.connected = False

        def create_db():
            db = Database()
            db.connected = True
            return db

        # 执行
        container.register_factory("database", create_db)
        db = container.resolve("database")

        # 断言
        assert isinstance(db, Database)
        assert db.connected is True


class TestLifetimes:
    """生命周期测试."""

    def test_singleton_lifetime(self, container) -> None:
        """测试单例生命周期."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SINGLETON)
        service1 = container.resolve(Service)
        service2 = container.resolve(Service)

        # 断言
        assert service1 is service2

    def test_transient_lifetime(self, container) -> None:
        """测试瞬时生命周期."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.TRANSIENT)
        service1 = container.resolve(Service)
        service2 = container.resolve(Service)

        # 断言
        assert service1 is not service2

    def test_scoped_lifetime(self, container) -> None:
        """测试作用域生命周期."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SCOPED)

        # 在作用域内解析
        with container.create_scope() as scope:
            service1 = scope.resolve(Service)
            service2 = scope.resolve(Service)
            # 同一作用域内应该是同一实例
            assert service1 is service2

    def test_factory_lifetime(self, container) -> None:
        """测试工厂生命周期."""
        # 准备
        counter = 0

        def factory():
            nonlocal counter
            counter += 1
            return counter

        # 执行
        container.register_factory("counter", factory, lifetime=Lifetime.FACTORY)
        result1 = container.resolve("counter")
        result2 = container.resolve("counter")

        # 断言
        assert result1 == 1
        assert result2 == 2

    @pytest.mark.parametrize(
        "lifetime",
        [
            Lifetime.SINGLETON,
            Lifetime.TRANSIENT,
            Lifetime.SCOPED,
        ],
    )
    def test_different_lifetimes(self, container, lifetime) -> None:
        """使用参数化测试不同的生命周期."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=lifetime)

        if lifetime == Lifetime.SCOPED:
            # 作用域需要特殊处理
            with container.create_scope() as scope:
                service1 = scope.resolve(Service)
                service2 = scope.resolve(Service)
                # 同一作用域内应该是相同实例
                assert service1 is service2
        else:
            service1 = container.resolve(Service)
            service2 = container.resolve(Service)

            if lifetime == Lifetime.SINGLETON:
                assert service1 is service2
            else:
                assert service1 is not service2


class TestErrorHandling:
    """错误处理测试."""

    def test_resolve_nonexistent_service(self, container) -> None:
        """测试解析不存在的服务抛出异常."""
        # 执行 & 断言
        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.resolve("non_existent")

        assert "non_existent" in str(exc_info.value)

    def test_register_duplicate_without_override(self, container) -> None:
        """测试重复注册而不覆盖会抛出异常."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service)

        # 断言
        with pytest.raises(RegistrationError):
            container.register(Service)

    def test_register_duplicate_with_override(self, container) -> None:
        """测试使用 override=True 覆盖已注册的服务."""

        # 准备
        class Service:
            pass

        class NewService(Service):
            pass

        # 执行
        container.register(Service)
        container.register(NewService, key=Service, override=True)
        result = container.resolve(Service)

        # 断言
        assert isinstance(result, NewService)

    def test_circular_dependency_detection(self, container) -> None:
        """测试循环依赖检测."""
        # 准备 - 这需要依赖注入功能,暂时跳过
        # 后续在测试注入功能时完成

    def test_resolution_error(self, container) -> None:
        """测试解析错误处理."""

        # 准备
        def bad_factory() -> Never:
            msg = "工厂失败"
            raise ValueError(msg)

        # 执行
        container.register_factory("bad", bad_factory)

        # 断言
        with pytest.raises(ResolutionError):
            container.resolve("bad")


class TestChainedRegistration:
    """链式注册测试."""

    def test_chained_registration(self, container) -> None:
        """测试链式注册调用."""

        # 准备
        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        # 执行
        result = container.register(ServiceA).register(ServiceB).register(ServiceC)

        # 断言
        assert result is container
        assert container.is_registered(ServiceA)
        assert container.is_registered(ServiceB)
        assert container.is_registered(ServiceC)


class TestInspection:
    """容器检查方法测试."""

    def test_is_registered(self, container) -> None:
        """测试 is_registered 方法."""

        # 准备
        class Service:
            pass

        # 执行 & 断言
        assert not container.is_registered(Service)

        container.register(Service)
        assert container.is_registered(Service)

    def test_get_registration(self, container) -> None:
        """测试 get_registration 方法."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SINGLETON)
        registration = container.get_registration(Service)

        # 断言
        assert registration is not None
        assert registration.key == Service
        assert registration.lifetime == Lifetime.SINGLETON

    def test_get_all_registrations(self, container) -> None:
        """测试 get_all_registrations 方法."""

        # 准备
        class ServiceA:
            pass

        class ServiceB:
            pass

        # 执行
        container.register(ServiceA)
        container.register(ServiceB)
        all_registrations = container.get_all_registrations()

        # 断言
        assert len(all_registrations) == 2
        assert ServiceA in all_registrations
        assert ServiceB in all_registrations


class TestContextManager:
    """上下文管理器测试."""

    def test_container_as_context_manager(self) -> None:
        """测试容器作为上下文管理器."""
        # 执行
        with Container() as container:

            class Service:
                pass

            container.register(Service)
            service = container.resolve(Service)
            assert isinstance(service, Service)

        # 容器已释放
        assert container._registrations == {}
