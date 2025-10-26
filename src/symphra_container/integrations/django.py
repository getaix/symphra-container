"""Django 框架集成.

⚠️ 需要安装: pip install symphra-container[django]

示例:
    # 1. 在 settings.py 中配置
    from symphra_container import Container, Lifetime
    from symphra_container.integrations import DjangoContainer

    # 创建容器
    CONTAINER = Container()
    CONTAINER.register(UserService, lifetime=Lifetime.SCOPED)
    CONTAINER.register(EmailService, lifetime=Lifetime.TRANSIENT)

    # 配置 Django 集成
    MIDDLEWARE = [
        'symphra_container.integrations.django.ContainerMiddleware',
        # ... 其他中间件
    ]

    # 2. 在视图中使用
    from symphra_container.integrations import DjangoContainer

    def user_view(request, user_id):
        user_service = DjangoContainer.resolve(UserService)
        user = user_service.get_user(user_id)
        return JsonResponse(user.to_dict())

    # 或使用装饰器
    @DjangoContainer.inject
    def email_view(request, email_service: EmailService):
        email_service.send("test@example.com", "Hello")
        return JsonResponse({"status": "sent"})
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from symphra_container.container import Container

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

__all__ = ["ContainerMiddleware", "DjangoContainer"]


class DjangoContainer:
    """Django 应用的容器包装器.

    提供与 Django 请求生命周期集成的依赖注入功能。

    Attributes:
        _container: 全局容器实例

    示例:
        >>> # 在 settings.py 中
        >>> from django.conf import settings
        >>> settings.CONTAINER = Container()
        >>> # 在视图中
        >>> user_service = DjangoContainer.resolve(UserService)
    """

    _container: Container | None = None

    @classmethod
    def setup(cls, container: Container) -> None:
        """设置全局容器实例.

        通常在 settings.py 或应用启动时调用。

        Args:
            container: 容器实例

        Raises:
            ImportError: 如果未安装 Django

        示例:
            >>> from django.conf import settings
            >>> container = Container()
            >>> DjangoContainer.setup(container)
        """
        try:
            import django  # noqa: F401
        except ImportError as e:
            raise ImportError("Django is not installed. Install it with: pip install symphra-container[django]") from e

        cls._container = container

    @classmethod
    def get_container(cls) -> Container:
        """获取全局容器实例.

        Returns:
            Container: 容器实例

        Raises:
            RuntimeError: 如果容器未初始化

        示例:
            >>> container = DjangoContainer.get_container()
        """
        if cls._container is None:
            # 尝试从 Django settings 获取
            try:
                from django.conf import settings

                if hasattr(settings, "CONTAINER"):
                    cls._container = settings.CONTAINER
            except Exception:
                pass

        if cls._container is None:
            raise RuntimeError("Container not initialized. Call DjangoContainer.setup() or set settings.CONTAINER")

        return cls._container

    @classmethod
    def resolve(cls, service_type: type[T]) -> T:
        """解析服务实例.

        在请求上下文中使用作用域容器(如果有)，否则使用根容器。

        Args:
            service_type: 要解析的服务类型

        Returns:
            T: 服务实例

        Raises:
            RuntimeError: 如果容器未初始化
            ServiceNotFoundError: 如果服务未注册

        示例:
            >>> user_service = DjangoContainer.resolve(UserService)
        """
        # 尝试从当前线程获取请求对象
        try:
            import threading

            local = threading.local()
            request: HttpRequest | None = getattr(local, "request", None)
            if request and hasattr(request, "container_scope"):
                return request.container_scope.resolve(service_type)
        except Exception:
            pass

        # 使用根容器
        container = cls.get_container()
        return container.resolve(service_type)

    @classmethod
    def inject(cls, func: F) -> F:
        """装饰器: 自动注入函数参数.

        分析函数签名(跳过 request 参数)，根据类型注解自动注入服务。

        Args:
            func: 要装饰的函数(Django 视图函数)

        Returns:
            F: 装饰后的函数

        Raises:
            RuntimeError: 如果服务解析失败

        示例:
            >>> @DjangoContainer.inject
            ... def view(request, user_service: UserService):
            ...     return JsonResponse(user_service.get_all())
        """
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 分析需要注入的参数
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            for param_name, param in sig.parameters.items():
                # 跳过 request 参数和已提供的参数
                if param_name == "request" or param_name in bound_args.arguments:
                    continue

                # 检查是否有类型注解
                if param.annotation == inspect.Parameter.empty:
                    continue

                # 尝试解析服务
                try:
                    service = cls.resolve(param.annotation)
                    bound_args.arguments[param_name] = service
                except Exception:
                    # 无法解析，可能不是容器管理的服务
                    continue

            return func(*bound_args.args, **bound_args.kwargs)

        return cast(F, wrapper)


class ContainerMiddleware:
    """Django 中间件: 管理请求作用域.

    在每个请求开始时创建作用域，请求结束时清理。

    示例:
        >>> # 在 settings.py 中
        >>> MIDDLEWARE = [
        ...     'symphra_container.integrations.django.ContainerMiddleware',
        ...     # ... 其他中间件
        ... ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """初始化中间件.

        Args:
            get_response: Django 视图处理函数
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """处理请求.

        Args:
            request: Django 请求对象

        Returns:
            HttpResponse: 响应对象
        """
        # 创建作用域
        container = DjangoContainer.get_container()
        scope = container.create_scope()

        # 将作用域附加到请求对象
        request.container_scope = scope  # type: ignore

        # 同时设置到线程本地存储
        import threading

        local = threading.local()
        local.request = request

        try:
            return self.get_response(request)
        finally:
            # 清理作用域
            scope.dispose()
            local.request = None
