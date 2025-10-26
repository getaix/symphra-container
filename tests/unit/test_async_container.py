"""异步容器测试.

测试异步依赖注入容器的功能:
- 异步工厂函数注册
- 异步依赖解析
- 混合同步和异步依赖
- 生命周期管理
"""

import asyncio
from typing import Never

import pytest

from symphra_container import (
    AsyncContainer,
    Lifetime,
    ServiceNotFoundError,
)


class TestAsyncContainerBasics:
    """异步容器基础测试."""

    @pytest.mark.asyncio
    async def test_async_container_creation(self) -> None:
        """测试异步容器创建."""
        # 执行
        container = AsyncContainer()

        # 断言
        assert container is not None
        assert isinstance(container, AsyncContainer)

    @pytest.mark.asyncio
    async def test_register_sync_service_in_async_container(self) -> None:
        """测试在异步容器中注册同步服务."""

        # 准备
        class Service:
            pass

        # 执行
        container = AsyncContainer()
        container.register(Service)

        # 断言
        assert container.is_registered(Service)

    @pytest.mark.asyncio
    async def test_resolve_sync_service_in_async_container(self) -> None:
        """测试在异步容器中解析同步服务."""

        # 准备
        class Service:
            pass

        # 执行
        container = AsyncContainer()
        container.register(Service)
        service = await container.resolve_async(Service)

        # 断言
        assert isinstance(service, Service)


class TestAsyncFactory:
    """异步工厂函数测试."""

    @pytest.mark.asyncio
    async def test_register_async_factory(self) -> None:
        """测试注册异步工厂函数."""

        # 准备
        async def async_factory() -> str:
            await asyncio.sleep(0)
            return "async_value"

        # 执行
        container = AsyncContainer()
        container.register_async_factory("service", async_factory)

        # 断言
        assert container.is_registered("service")

    @pytest.mark.asyncio
    async def test_resolve_async_factory(self) -> None:
        """测试解析异步工厂函数."""

        # 准备
        async def async_factory() -> str:
            await asyncio.sleep(0)
            return "async_value"

        # 执行
        container = AsyncContainer()
        container.register_async_factory("service", async_factory)
        result = await container.resolve_async("service")

        # 断言
        assert result == "async_value"

    @pytest.mark.asyncio
    async def test_async_factory_called_each_time_transient(self) -> None:
        """测试瞬时异步工厂每次都被调用."""
        # 准备
        call_count = 0

        async def async_factory() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0)
            return f"value_{call_count}"

        # 执行
        container = AsyncContainer()
        container.register_async_factory(
            "service",
            async_factory,
            lifetime=Lifetime.TRANSIENT,
        )

        result1 = await container.resolve_async("service")
        result2 = await container.resolve_async("service")

        # 断言
        assert result1 == "value_1"
        assert result2 == "value_2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_factory_with_singleton_lifetime(self) -> None:
        """测试单例异步工厂."""
        # 准备
        call_count = 0

        async def async_factory():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0)
            return {"count": call_count}

        # 执行
        container = AsyncContainer()
        container.register_async_factory(
            "service",
            async_factory,
            lifetime=Lifetime.SINGLETON,
        )

        result1 = await container.resolve_async("service")
        result2 = await container.resolve_async("service")

        # 断言
        assert call_count == 1
        assert result1 == {"count": 1}
        assert result2 == {"count": 1}
        assert result1 is result2


class TestAsyncDependencies:
    """异步依赖测试."""

    @pytest.mark.asyncio
    async def test_async_dependency_resolution(self) -> None:
        """测试异步依赖解析."""

        # 准备
        class DatabaseConnection:
            async def connect(self) -> str:
                await asyncio.sleep(0)
                return "connected"

        async def create_db():
            db = DatabaseConnection()
            await db.connect()
            return db

        class UserService:
            def __init__(self, db: DatabaseConnection) -> None:
                self.db = db

        # 执行
        container = AsyncContainer()
        container.register_async_factory(DatabaseConnection, create_db)
        container.register(UserService)

        service = await container.resolve_async(UserService)

        # 断言
        assert isinstance(service, UserService)
        assert isinstance(service.db, DatabaseConnection)

    @pytest.mark.asyncio
    async def test_mixed_sync_and_async_dependencies(self) -> None:
        """测试混合同步和异步依赖."""

        # 准备
        class Logger:
            pass

        class Config:
            pass

        async def async_logger_factory():
            await asyncio.sleep(0)
            return Logger()

        class Service:
            def __init__(self, logger: Logger, config: Config) -> None:
                self.logger = logger
                self.config = config

        # 执行
        container = AsyncContainer()
        container.register_async_factory(Logger, async_logger_factory)
        container.register(Config)
        container.register(Service)

        service = await container.resolve_async(Service)

        # 断assert
        assert isinstance(service, Service)
        assert isinstance(service.logger, Logger)
        assert isinstance(service.config, Config)

    @pytest.mark.asyncio
    async def test_async_dependency_chain(self) -> None:
        """测试异步依赖链."""

        # 准备
        class Level3:
            pass

        class Level2:
            def __init__(self, l3: Level3) -> None:
                self.l3 = l3

        class Level1:
            def __init__(self, l2: Level2) -> None:
                self.l2 = l2

        async def create_level3():
            await asyncio.sleep(0)
            return Level3()

        # 执行
        container = AsyncContainer()
        container.register_async_factory(Level3, create_level3)
        container.register(Level2)
        container.register(Level1)

        l1 = await container.resolve_async(Level1)

        # 断言
        assert isinstance(l1, Level1)
        assert isinstance(l1.l2, Level2)
        assert isinstance(l1.l2.l3, Level3)


class TestAsyncInstanceRegistration:
    """异步容器实例注册测试."""

    @pytest.mark.asyncio
    async def test_register_instance_in_async_container(self) -> None:
        """测试在异步容器中注册实例."""
        # 准备
        instance = {"value": 42}

        # 执行
        container = AsyncContainer()
        container.register_instance("config", instance)

        # 断言
        assert container.is_registered("config")

    @pytest.mark.asyncio
    async def test_resolve_registered_instance(self) -> None:
        """测试解析已注册的实例."""
        # 准备
        original_instance = {"value": 42}

        # 执行
        container = AsyncContainer()
        container.register_instance("config", original_instance)
        resolved = await container.resolve_async("config")

        # 断言
        assert resolved is original_instance
        assert resolved == {"value": 42}


class TestAsyncContainerErrors:
    """异步容器错误处理测试."""

    @pytest.mark.asyncio
    async def test_resolve_unregistered_service(self) -> None:
        """测试解析未注册的服务."""
        # 执行 & 断言
        container = AsyncContainer()

        with pytest.raises(ServiceNotFoundError):
            await container.resolve_async("missing")

    @pytest.mark.asyncio
    async def test_async_factory_exception(self) -> None:
        """测试异步工厂异常处理."""

        # 准备
        async def failing_factory() -> Never:
            await asyncio.sleep(0)
            msg = "Factory failed!"
            raise ValueError(msg)

        # 执行 & 断言
        container = AsyncContainer()
        container.register_async_factory("service", failing_factory)

        from symphra_container.exceptions import ResolutionError

        with pytest.raises(ResolutionError):
            await container.resolve_async("service")

    @pytest.mark.asyncio
    async def test_duplicate_registration_error(self) -> None:
        """测试重复注册错误."""
        from symphra_container.exceptions import RegistrationError

        # 准备
        async def factory1() -> str:
            return "value1"

        async def factory2() -> str:
            return "value2"

        # 执行 & 断言
        container = AsyncContainer()
        container.register_async_factory("service", factory1)

        with pytest.raises(RegistrationError):
            container.register_async_factory("service", factory2, override=False)

    @pytest.mark.asyncio
    async def test_override_registration(self) -> None:
        """测试覆盖注册."""

        # 准备
        async def factory1() -> str:
            return "value1"

        async def factory2() -> str:
            return "value2"

        # 执行
        container = AsyncContainer()
        container.register_async_factory("service", factory1)
        container.register_async_factory("service", factory2, override=True)
        result = await container.resolve_async("service")

        # 断言
        assert result == "value2"


class TestAsyncContextManager:
    """异步容器上下文管理器测试."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """测试异步上下文管理器."""

        # 准备
        class Service:
            pass

        # 执行
        async with AsyncContainer() as container:
            container.register(Service)
            service = await container.resolve_async(Service)

            # 断言
            assert isinstance(service, Service)

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup(self) -> None:
        """测试异步上下文管理器清理."""

        # 准备
        async def cleanup_factory() -> str:
            await asyncio.sleep(0)
            return "value"

        # 执行
        async with AsyncContainer() as container:
            container.register_async_factory("service", cleanup_factory)
            service = await container.resolve_async("service")
            assert service == "value"

        # 离开上下文后,注册应该被清空
        assert not container.is_registered("service")


class TestAsyncContainerChaining:
    """异步容器链式调用测试."""

    @pytest.mark.asyncio
    async def test_registration_chaining(self) -> None:
        """测试注册链式调用."""

        # 准备
        class ServiceA:
            pass

        class ServiceB:
            pass

        async def factory_c() -> str:
            await asyncio.sleep(0)
            return "service_c"

        # 执行
        container = AsyncContainer()
        result = (
            container.register(ServiceA)
            .register(ServiceB)
            .register_async_factory("c", factory_c)
            .register_instance("config", {})
        )

        # 断言
        assert result is container
        assert container.is_registered(ServiceA)
        assert container.is_registered(ServiceB)
        assert container.is_registered("c")
        assert container.is_registered("config")


class TestAsyncRegistrationInfo:
    """异步容器注册信息测试."""

    @pytest.mark.asyncio
    async def test_get_registration(self) -> None:
        """测试获取注册信息."""

        # 准备
        class Service:
            pass

        # 执行
        container = AsyncContainer()
        container.register(Service, lifetime=Lifetime.SINGLETON)
        registration = container.get_registration(Service)

        # 断言
        assert registration is not None
        assert registration.key is Service
        assert registration.lifetime == Lifetime.SINGLETON

    @pytest.mark.asyncio
    async def test_get_all_registrations(self) -> None:
        """测试获取所有注册信息."""

        # 准备
        class ServiceA:
            pass

        class ServiceB:
            pass

        # 执行
        container = AsyncContainer()
        container.register(ServiceA)
        container.register(ServiceB)
        container.register_instance("config", {})

        registrations = container.get_all_registrations()

        # 断言
        assert len(registrations) == 3
        assert ServiceA in registrations
        assert ServiceB in registrations
        assert "config" in registrations
