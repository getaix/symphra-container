"""FastAPI 框架集成.

⚠️ 需要安装: pip install symphra-container[fastapi]

示例:
    from symphra_container import Container
    from symphra_container.integrations import fastapi_inject, setup_fastapi
    from fastapi import FastAPI, Depends

    # 1. 设置容器
    container = Container()
    container.register(UserService, lifetime=Lifetime.SCOPED)
    container.register(EmailService, lifetime=Lifetime.TRANSIENT)

    # 2. 绑定到 FastAPI
    app = FastAPI()
    setup_fastapi(app, container)

    # 3. 在路由中使用依赖注入
    @app.get("/users/{user_id}")
    async def get_user(
        user_id: int,
        user_service: UserService = Depends(fastapi_inject(UserService))
    ):
        user = await user_service.get_user(user_id)
        return user
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI

    from symphra_container.container import Container

T = TypeVar("T")

__all__ = ["get_container", "inject", "setup_container"]


# 全局容器实例
_container: Container | None = None
_lifespan_managed = False


def setup_container(app: FastAPI, container: Container) -> None:
    """将容器绑定到 FastAPI 应用.

    此函数会:
    1. 将容器存储到全局变量中供 inject() 使用
    2. 配置生命周期管理(自动处理 SCOPED 服务)

    Args:
        app: FastAPI 应用实例
        container: 容器实例

    Raises:
        ImportError: 如果未安装 FastAPI

    示例:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> container = Container()
        >>> setup_container(app, container)
    """
    try:
        from fastapi import FastAPI
    except ImportError as e:
        raise ImportError("FastAPI is not installed. Install it with: pip install symphra-container[fastapi]") from e

    global _container, _lifespan_managed
    _container = container

    # 注册生命周期钩子管理 SCOPED 作用域
    if not _lifespan_managed:
        original_lifespan = app.router.lifespan_context

        async def managed_lifespan(app_instance: FastAPI):
            """管理请求作用域生命周期."""
            async with container:  # 进入容器上下文
                if original_lifespan:
                    async with original_lifespan(app_instance):
                        yield
                else:
                    yield

        app.router.lifespan_context = managed_lifespan
        _lifespan_managed = True


def get_container() -> Container:
    """获取全局容器实例.

    Returns:
        Container: 当前绑定的容器实例

    Raises:
        RuntimeError: 如果容器未初始化

    示例:
        >>> container = get_container()
        >>> service = container.resolve(MyService)
    """
    if _container is None:
        raise RuntimeError("Container not initialized. Call setup_container() first.")
    return _container


def inject(service_type: type[T]) -> Callable[[], T]:
    """创建 FastAPI 依赖注入函数.

    用于在 FastAPI 路由中注入服务。返回的函数可以作为 Depends() 的参数。

    Args:
        service_type: 要注入的服务类型

    Returns:
        Callable: 可用于 Depends() 的依赖函数

    Raises:
        RuntimeError: 如果容器未初始化
        ServiceNotFoundError: 如果服务未注册

    示例:
        >>> @app.get("/users")
        >>> async def get_users(
        ...     user_service: UserService = Depends(inject(UserService))
        ... ):
        ...     return await user_service.get_all()
    """

    def dependency() -> T:
        container = get_container()
        # 检查是否是异步服务
        registration = container._registrations.get(service_type)
        if registration and registration.is_async:
            # 异步服务需要用 resolve_async, 但这里是同步上下文
            # FastAPI 会自动处理异步依赖，所以这里直接返回 coroutine
            import asyncio

            coro = container.resolve_async(service_type)
            # 如果当前已经在 async 上下文中，直接返回 coroutine
            # FastAPI 会自动 await 它
            try:
                asyncio.get_running_loop()
                # 在 async 上下文中，返回 coroutine 让 FastAPI await
                return coro  # type: ignore
            except RuntimeError:
                # 不在 async 上下文中，尝试同步解析
                return container.resolve(service_type)
        else:
            # 同步服务直接解析
            return container.resolve(service_type)

    return dependency
