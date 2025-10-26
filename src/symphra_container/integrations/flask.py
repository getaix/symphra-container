"""Flask 框架集成.

⚠️ 需要安装: pip install symphra-container[flask]

示例:
    from symphra_container import Container, Lifetime
    from symphra_container.integrations import FlaskContainer
    from flask import Flask

    # 1. 创建容器
    container = Container()
    container.register(UserService, lifetime=Lifetime.SCOPED)
    container.register(EmailService, lifetime=Lifetime.TRANSIENT)

    # 2. 创建 Flask 应用并集成容器
    app = Flask(__name__)
    flask_container = FlaskContainer(app, container)

    # 3. 在视图中使用依赖注入
    @app.route("/users/<int:user_id>")
    @flask_container.inject
    def get_user(user_id: int, user_service: UserService):
        user = user_service.get_user(user_id)
        return user.to_dict()

    # 或者手动获取服务
    @app.route("/emails")
    def send_email():
        email_service = flask_container.resolve(EmailService)
        email_service.send("test@example.com", "Hello")
        return {"status": "sent"}
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast, get_type_hints

if TYPE_CHECKING:
    from flask import Flask

    from symphra_container.container import Container

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

__all__ = ["FlaskContainer"]


class FlaskContainer:
    """Flask 应用的容器包装器.

    提供与 Flask 请求生命周期集成的依赖注入功能。

    Attributes:
        app: Flask 应用实例
        container: 容器实例

    示例:
        >>> app = Flask(__name__)
        >>> container = Container()
        >>> flask_container = FlaskContainer(app, container)
        >>> @flask_container.inject
        ... def view(user_service: UserService):
        ...     return user_service.get_users()
    """

    def __init__(self, app: Flask, container: Container) -> None:
        """初始化 Flask 容器.

        Args:
            app: Flask 应用实例
            container: 容器实例

        Raises:
            ImportError: 如果未安装 Flask
        """
        try:
            from flask import Flask, g
        except ImportError as e:
            raise ImportError("Flask is not installed. Install it with: pip install symphra-container[flask]") from e

        self.app = app
        self.container = container
        self._flask_g = g

        # 注册应用上下文钩子来管理作用域
        @app.teardown_appcontext
        def teardown_context(exception: Exception | None = None) -> None:
            """在应用上下文结束时清理作用域."""
            scope = getattr(g, "container_scope", None)
            if scope:
                scope.__exit__(None, None, None)  # 正确退出作用域

    def resolve(self, service_type: type[T]) -> T:
        """解析服务实例.

        在请求上下文中使用作用域容器，否则使用根容器。

        Args:
            service_type: 要解析的服务类型

        Returns:
            T: 服务实例

        Raises:
            RuntimeError: 如果不在请求上下文中且服务是 SCOPED
            ServiceNotFoundError: 如果服务未注册

        示例:
            >>> user_service = flask_container.resolve(UserService)
        """
        try:
            from flask import g

            # 如果还没有作用域,创建一个
            scope = getattr(g, "container_scope", None)
            if scope is None:
                scope = self.container.create_scope()
                scope.__enter__()  # 激活作用域
                g.container_scope = scope

            return scope.resolve(service_type)
        except RuntimeError:
            # 不在请求上下文中
            pass

        return self.container.resolve(service_type)

    def inject(self, func: F) -> F:
        """装饰器: 自动注入函数参数.

        分析函数签名，根据类型注解自动注入服务。

        Args:
            func: 要装饰的函数

        Returns:
            F: 装饰后的函数

        Raises:
            RuntimeError: 如果服务解析失败

        示例:
            >>> @flask_container.inject
            ... def view(user_service: UserService, email_service: EmailService):
            ...     # user_service 和 email_service 会自动注入
            ...     return user_service.get_all()
        """
        sig = inspect.signature(func)

        # 获取函数的类型提示, 用于解析字符串注解
        try:
            type_hints = get_type_hints(func)
        except (NameError, TypeError):
            # 如果无法获取类型提示, 使用空的字典
            type_hints = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 获取所有参数的绑定
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()

            # 收集需要注入的参数
            for param_name, param in sig.parameters.items():
                # 跳过已提供的参数
                if param_name in bound.arguments:
                    continue

                # 检查是否有类型注解
                if param.annotation == inspect.Parameter.empty:
                    continue

                # 解析注解类型
                annotation = type_hints.get(param_name, param.annotation)
                if annotation == inspect.Parameter.empty:
                    continue

                # 尝试解析服务
                try:
                    service = self.resolve(annotation)
                    bound.arguments[param_name] = service
                except Exception as e:
                    # 无法解析, 可能不是容器管理的服务
                    # 注意: 如果这是容器管理的服务但解析失败, 应该抛出异常
                    if hasattr(e, '__class__') and "ServiceNotFoundError" in e.__class__.__name__:
                        # 服务未找到, 可能确实不是容器管理的
                        continue
                    # 其他异常应该重新抛出
                    raise

            # 调用函数, 使用完整的参数字典
            return func(**bound.arguments)

        return cast("F", wrapper)
