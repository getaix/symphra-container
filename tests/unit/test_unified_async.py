"""测试统一容器的异步支持.

验证 Container 同时支持同步和异步服务的功能.
"""

import asyncio

import pytest

from symphra_container import Container
from symphra_container.exceptions import ResolutionError
from symphra_container.types import Lifetime


# 测试服务类
class SyncService:
    """同步服务."""

    def __init__(self) -> None:
        self.name = "sync"


class AsyncService:
    """异步服务."""

    def __init__(self) -> None:
        self.name = "async"
        self.initialized = False

    async def initialize(self) -> None:
        """异步初始化."""
        await asyncio.sleep(0.01)
        self.initialized = True


class MixedService:
    """混合依赖服务."""

    def __init__(self, sync: SyncService, async_svc: AsyncService) -> None:
        self.sync = sync
        self.async_svc = async_svc


# 异步工厂函数
async def create_async_service() -> AsyncService:
    """异步创建服务."""
    service = AsyncService()
    await service.initialize()
    return service


# 同步工厂函数
def create_sync_service() -> SyncService:
    """同步创建服务."""
    return SyncService()


class TestUnifiedContainer:
    """测试统一容器."""

    def test_sync_service(self) -> None:
        """测试同步服务解析."""
        container = Container()
        container.register(SyncService)

        # 同步解析
        service = container.resolve(SyncService)
        assert isinstance(service, SyncService)
        assert service.name == "sync"

    @pytest.mark.asyncio
    async def test_async_service(self) -> None:
        """测试异步服务解析."""
        container = Container()
        container.register_factory(AsyncService, create_async_service)

        # 异步解析
        service = await container.resolve_async(AsyncService)
        assert isinstance(service, AsyncService)
        assert service.initialized is True

    def test_sync_resolve_async_service_fails(self) -> None:
        """测试同步解析异步服务应该失败."""
        container = Container()
        container.register_factory(AsyncService, create_async_service)

        # 应该抛出错误
        with pytest.raises(ResolutionError) as exc_info:
            container.resolve(AsyncService)

        assert "async factory" in str(exc_info.value).lower()
        assert "resolve_async" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_resolve_sync_service(self) -> None:
        """测试异步解析同步服务(应该正常工作)."""
        container = Container()
        container.register(SyncService)

        # 异步解析同步服务
        service = await container.resolve_async(SyncService)
        assert isinstance(service, SyncService)
        assert service.name == "sync"

    @pytest.mark.asyncio
    async def test_mixed_dependencies(self) -> None:
        """测试混合同步和异步依赖."""
        container = Container()
        container.register(SyncService)
        container.register_factory(AsyncService, create_async_service)
        container.register(MixedService)

        # 异步解析混合服务
        service = await container.resolve_async(MixedService)
        assert isinstance(service, MixedService)
        assert isinstance(service.sync, SyncService)
        assert isinstance(service.async_svc, AsyncService)
        assert service.async_svc.initialized is True

    @pytest.mark.asyncio
    async def test_try_resolve_async(self) -> None:
        """测试 try_resolve_async."""
        container = Container()

        # 服务不存在,返回默认值
        service = await container.try_resolve_async(AsyncService, default=None)
        assert service is None

        # 注册后可以解析
        container.register_factory(AsyncService, create_async_service)
        service = await container.try_resolve_async(AsyncService)
        assert isinstance(service, AsyncService)

    @pytest.mark.asyncio
    async def test_warmup_async(self) -> None:
        """测试异步预热."""
        container = Container()
        container.register_factory(AsyncService, create_async_service, lifetime=Lifetime.SINGLETON)

        # 预热
        await container.warmup_async()

        # 再次解析应该返回相同实例(已缓存)
        service1 = await container.resolve_async(AsyncService)
        service2 = await container.resolve_async(AsyncService)
        assert service1 is service2

    def test_registration_auto_detect_async(self) -> None:
        """测试注册时自动检测异步工厂."""
        container = Container()

        # 注册异步工厂
        container.register_factory(AsyncService, create_async_service)
        registration = container._registrations[AsyncService]
        assert registration.is_async is True

        # 注册同步工厂
        container.register_factory(SyncService, create_sync_service)
        registration = container._registrations[SyncService]
        assert registration.is_async is False

    @pytest.mark.asyncio
    async def test_async_singleton(self) -> None:
        """测试异步单例."""
        container = Container()
        container.register_factory(AsyncService, create_async_service, lifetime=Lifetime.SINGLETON)

        # 多次解析应该返回相同实例
        service1 = await container.resolve_async(AsyncService)
        service2 = await container.resolve_async(AsyncService)
        assert service1 is service2
        assert service1.initialized is True

    @pytest.mark.asyncio
    async def test_async_transient(self) -> None:
        """测试异步瞬态."""
        container = Container()
        container.register_factory(AsyncService, create_async_service, lifetime=Lifetime.TRANSIENT)

        # 多次解析应该返回不同实例
        service1 = await container.resolve_async(AsyncService)
        service2 = await container.resolve_async(AsyncService)
        assert service1 is not service2

    def test_service_registration_repr_with_async(self) -> None:
        """测试 ServiceRegistration 的字符串表示包含异步标记."""
        container = Container()
        container.register_factory(AsyncService, create_async_service)

        registration = container._registrations[AsyncService]
        repr_str = repr(registration)
        assert "[async]" in repr_str
        assert "AsyncService" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
