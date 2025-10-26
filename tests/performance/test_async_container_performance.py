"""异步容器性能测试.

测试 AsyncContainer 的异步操作性能:
- 异步服务解析
- 异步资源管理
- 异步依赖注入
- 并发异步操作
"""

import asyncio

import pytest

from symphra_container import AsyncContainer, Lifetime

# ============================================================================
# 测试夹具
# ============================================================================


@pytest.fixture
def async_container():
    """创建一个异步容器实例."""
    return AsyncContainer()


@pytest.fixture
def async_service():
    """简单异步服务类."""

    class AsyncService:
        async def initialize(self) -> None:
            await asyncio.sleep(0.001)  # 模拟异步初始化

        async def get_data(self) -> str:
            return "data"

    return AsyncService


# ============================================================================
# 异步解析性能测试
# ============================================================================


def test_async_resolve_singleton_performance(benchmark, async_container, async_service):
    """测试异步解析单例服务的性能."""
    async_container.register(async_service, lifetime=Lifetime.SINGLETON)

    async def resolve():
        return await async_container.resolve_async(async_service)

    # 使用 asyncio.run 运行异步函数
    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


def test_async_resolve_transient_performance(benchmark, async_container, async_service):
    """测试异步解析瞬态服务的性能."""
    async_container.register(async_service, lifetime=Lifetime.TRANSIENT)

    async def resolve():
        return await async_container.resolve_async(async_service)

    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


def test_async_resolve_with_dependencies_performance(benchmark, async_container):
    """测试异步解析带依赖的服务的性能."""

    class AsyncDatabase:
        async def connect(self) -> None:
            await asyncio.sleep(0.001)

    class AsyncCache:
        async def connect(self) -> None:
            await asyncio.sleep(0.001)

    class AsyncUserService:
        def __init__(self, db: AsyncDatabase, cache: AsyncCache) -> None:
            self.db = db
            self.cache = cache

        async def initialize(self) -> None:
            await self.db.connect()
            await self.cache.connect()

    async_container.register(AsyncDatabase, lifetime=Lifetime.SINGLETON)
    async_container.register(AsyncCache, lifetime=Lifetime.SINGLETON)
    async_container.register(AsyncUserService, lifetime=Lifetime.TRANSIENT)

    async def resolve():
        return await async_container.resolve_async(AsyncUserService)

    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


# ============================================================================
# 并发异步解析性能测试
# ============================================================================


def test_concurrent_async_resolution_performance(benchmark, async_container):
    """测试并发异步解析的性能."""

    class AsyncService:
        async def process(self) -> str:
            await asyncio.sleep(0.001)
            return "processed"

    async_container.register(AsyncService, lifetime=Lifetime.TRANSIENT)

    async def resolve_concurrent():
        tasks = [async_container.resolve_async(AsyncService) for _ in range(10)]
        return await asyncio.gather(*tasks)

    def sync_wrapper():
        return asyncio.run(resolve_concurrent())

    result = benchmark(sync_wrapper)
    assert len(result) == 10


def test_concurrent_singleton_resolution_performance(benchmark, async_container):
    """测试并发解析单例服务的性能."""

    class AsyncSingletonService:
        async def initialize(self) -> None:
            await asyncio.sleep(0.001)

    async_container.register(AsyncSingletonService, lifetime=Lifetime.SINGLETON)

    async def resolve_concurrent():
        tasks = [async_container.resolve_async(AsyncSingletonService) for _ in range(10)]
        return await asyncio.gather(*tasks)

    def sync_wrapper():
        return asyncio.run(resolve_concurrent())

    result = benchmark(sync_wrapper)
    assert len(result) == 10
    # 验证所有结果是同一个实例
    assert len({id(r) for r in result}) == 1


# ============================================================================
# 异步资源管理性能测试
# ============================================================================


def test_async_context_manager_performance(benchmark, async_container):
    """测试异步上下文管理器的性能."""

    class AsyncResource:
        def __init__(self) -> None:
            self.opened = False
            self.closed = False

        async def open(self) -> None:
            await asyncio.sleep(0.001)
            self.opened = True

        async def close(self) -> None:
            await asyncio.sleep(0.001)
            self.closed = True

    async_container.register(AsyncResource, lifetime=Lifetime.SCOPED)

    async def use_resource():
        # Scope 使用同步上下文管理器, 然后使用容器的 resolve_async
        with async_container.create_scope():
            resource = await async_container.resolve_async(AsyncResource)
            await resource.open()
            return resource

    def sync_wrapper():
        return asyncio.run(use_resource())

    result = benchmark(sync_wrapper)
    assert result.opened


# ============================================================================
# 异步工厂性能测试
# ============================================================================


def test_async_factory_performance(benchmark, async_container):
    """测试异步工厂函数的性能."""

    async def create_async_service():
        await asyncio.sleep(0.001)
        return {"status": "created"}

    async_container.register_factory(
        "async_service",
        create_async_service,
        lifetime=Lifetime.TRANSIENT,
    )

    async def resolve():
        return await async_container.resolve_async("async_service")

    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


def test_async_factory_with_dependencies_performance(benchmark, async_container):
    """测试带依赖的异步工厂的性能."""

    class AsyncConfig:
        def __init__(self) -> None:
            self.value = "config"

    async def create_service(config: AsyncConfig):
        await asyncio.sleep(0.001)
        return {"config": config.value}

    # 注册配置和服务类
    async_container.register(AsyncConfig, lifetime=Lifetime.SINGLETON)

    # 创建包装工厂来解析依赖
    async def factory_wrapper():
        config = await async_container.resolve_async(AsyncConfig)
        return await create_service(config)

    async_container.register_factory(
        "service",
        factory_wrapper,
        lifetime=Lifetime.TRANSIENT,
    )

    async def resolve():
        return await async_container.resolve_async("service")

    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


# ============================================================================
# 异步作用域性能测试
# ============================================================================


def test_async_scope_creation_performance(benchmark, async_container):
    """测试创建异步作用域的性能."""

    def create():
        return async_container.create_scope()

    result = benchmark(create)
    assert result is not None


def test_async_scoped_service_resolution_performance(benchmark, async_container):
    """测试在异步作用域内解析服务的性能."""

    class AsyncScopedService:
        async def initialize(self) -> None:
            await asyncio.sleep(0.001)

    async_container.register(AsyncScopedService, lifetime=Lifetime.SCOPED)

    async def resolve():
        with async_container.create_scope():
            return await async_container.resolve_async(AsyncScopedService)

    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


def test_multiple_async_scopes_performance(benchmark, async_container):
    """测试管理多个异步作用域的性能."""

    class AsyncScopedService:
        pass

    async_container.register(AsyncScopedService, lifetime=Lifetime.SCOPED)

    async def create_and_resolve():
        results = []
        for _ in range(5):
            with async_container.create_scope():
                service = await async_container.resolve_async(AsyncScopedService)
                results.append(service)
        return results

    def sync_wrapper():
        return asyncio.run(create_and_resolve())

    result = benchmark(sync_wrapper)
    assert len(result) == 5


# ============================================================================
# 异步性能基准测试
# ============================================================================


def test_async_vs_sync_resolution_baseline(benchmark, async_container):
    """对比异步和同步解析的性能基准."""

    class SimpleService:
        pass

    async_container.register(SimpleService, lifetime=Lifetime.SINGLETON)

    # 预热
    asyncio.run(async_container.resolve_async(SimpleService))

    async def resolve():
        return await async_container.resolve_async(SimpleService)

    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


def test_async_batch_resolution_performance(benchmark, async_container):
    """测试批量异步解析的性能."""

    class Service1:
        pass

    class Service2:
        pass

    class Service3:
        pass

    class Service4:
        pass

    class Service5:
        pass

    async_container.register(Service1, lifetime=Lifetime.SINGLETON)
    async_container.register(Service2, lifetime=Lifetime.SINGLETON)
    async_container.register(Service3, lifetime=Lifetime.SINGLETON)
    async_container.register(Service4, lifetime=Lifetime.SINGLETON)
    async_container.register(Service5, lifetime=Lifetime.SINGLETON)

    async def resolve_all():
        return await asyncio.gather(
            async_container.resolve_async(Service1),
            async_container.resolve_async(Service2),
            async_container.resolve_async(Service3),
            async_container.resolve_async(Service4),
            async_container.resolve_async(Service5),
        )

    def sync_wrapper():
        return asyncio.run(resolve_all())

    result = benchmark(sync_wrapper)
    assert len(result) == 5


# ============================================================================
# 大规模异步操作性能测试
# ============================================================================


def test_large_scale_async_resolution_performance(benchmark, async_container):
    """测试大规模异步解析的性能."""
    services = []
    for i in range(50):

        class Service:
            pass

        key = f"service_{i}"
        async_container.register(Service, key=key, lifetime=Lifetime.SINGLETON)
        services.append(key)

    async def resolve_all():
        tasks = [async_container.resolve_async(key) for key in services]
        return await asyncio.gather(*tasks)

    def sync_wrapper():
        return asyncio.run(resolve_all())

    result = benchmark(sync_wrapper)
    assert len(result) == 50


def test_async_deep_dependency_chain_performance(benchmark, async_container):
    """测试异步深层依赖链的性能."""

    class Level1:
        pass

    class Level2:
        def __init__(self, l1: Level1) -> None:
            self.l1 = l1

    class Level3:
        def __init__(self, l2: Level2) -> None:
            self.l2 = l2

    class Level4:
        def __init__(self, l3: Level3) -> None:
            self.l3 = l3

    class Level5:
        def __init__(self, l4: Level4) -> None:
            self.l4 = l4

    async_container.register(Level1, lifetime=Lifetime.SINGLETON)
    async_container.register(Level2, lifetime=Lifetime.SINGLETON)
    async_container.register(Level3, lifetime=Lifetime.SINGLETON)
    async_container.register(Level4, lifetime=Lifetime.SINGLETON)
    async_container.register(Level5, lifetime=Lifetime.TRANSIENT)

    async def resolve():
        return await async_container.resolve_async(Level5)

    def sync_wrapper():
        return asyncio.run(resolve())

    result = benchmark(sync_wrapper)
    assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
