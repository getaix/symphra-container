"""异常类定义模块.

定义了容器系统中使用的所有自定义异常类型.
包括:
  - 服务未找到异常
  - 循环依赖异常
  - 类型错误异常
  - 注册错误异常
  - 解析错误异常
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ServiceKey


class ContainerException(Exception):
    """容器异常基类.

    所有容器相关异常都继承自此基类.

    Attributes:
        message: 异常消息
        service_key: 相关的服务键(如果适用)
    """

    def __init__(
        self,
        message: str,
        service_key: ServiceKey | None = None,
    ) -> None:
        """初始化容器异常.

        Args:
            message: 异常消息
            service_key: 相关的服务键
        """
        self.message = message
        self.service_key = service_key
        super().__init__(message)

    def __str__(self) -> str:
        """返回异常的字符串表示."""
        if self.service_key:
            return f"{self.__class__.__name__}: {self.message} (service_key: {self.service_key})"
        return f"{self.__class__.__name__}: {self.message}"


class ServiceNotFoundError(ContainerException):
    """服务未找到异常.

    当尝试解析一个未注册的服务时抛出此异常.

    Attributes:
        message: 异常消息
        service_key: 未找到的服务键
        registered_services: 已注册的服务列表

    Examples:
        >>> container = Container()
        >>> container.resolve("NonExistentService")
        Traceback (most recent call last):
            ...
        ServiceNotFoundError: Service 'NonExistentService' not found in container
    """

    def __init__(
        self,
        service_key: ServiceKey,
        registered_services: list[ServiceKey] | None = None,
    ) -> None:
        """初始化服务未找到异常.

        Args:
            service_key: 未找到的服务键
            registered_services: 已注册的服务列表
        """
        self.registered_services = registered_services or []
        message = f"Service '{service_key}' not found in container"
        if self.registered_services:
            # 建议相似的服务
            message += f". Registered services: {self.registered_services[:5]}"
        super().__init__(message, service_key)


class CircularDependencyError(ContainerException):
    """循环依赖异常.

    当检测到循环依赖时抛出此异常.

    Attributes:
        message: 异常消息
        dependency_chain: 依赖链
        circular_service_key: 导致循环的服务键

    Examples:
        >>> class A:
        ...     def __init__(self, b: "B"):
        ...         self.b = b
        >>> class B:
        ...     def __init__(self, a: A):
        ...         self.a = a
        >>> container = Container()
        >>> container.register(A)
        >>> container.register(B)
        >>> container.resolve(A)
        Traceback (most recent call last):
            ...
        CircularDependencyError: Circular dependency detected: A -> B -> A
    """

    def __init__(
        self,
        service_key: ServiceKey,
        dependency_chain: list[ServiceKey] | None = None,
    ) -> None:
        """初始化循环依赖异常.

        Args:
            service_key: 导致循环的服务键
            dependency_chain: 依赖链
        """
        self.dependency_chain = dependency_chain or []
        chain_str = " -> ".join(str(k) for k in self.dependency_chain)
        message = f"Circular dependency detected: {chain_str} -> {service_key}"
        super().__init__(message, service_key)


class TypeMismatchError(ContainerException):
    """类型不匹配异常.

    当依赖的类型与注册的服务类型不匹配时抛出此异常.

    Attributes:
        message: 异常消息
        expected_type: 预期的类型
        actual_type: 实际的类型
    """

    def __init__(
        self,
        service_key: ServiceKey,
        expected_type: type,
        actual_type: type,
    ) -> None:
        """初始化类型不匹配异常.

        Args:
            service_key: 服务键
            expected_type: 预期的类型
            actual_type: 实际的类型
        """
        self.expected_type = expected_type
        self.actual_type = actual_type
        message = (
            f"Type mismatch for service '{service_key}': expected {expected_type.__name__}, got {actual_type.__name__}"
        )
        super().__init__(message, service_key)


class RegistrationError(ContainerException):
    """注册错误异常.

    当服务注册失败时抛出此异常.

    Attributes:
        message: 异常消息
        service_key: 相关的服务键
        reason: 失败原因
    """

    def __init__(
        self,
        service_key: ServiceKey,
        reason: str,
    ) -> None:
        """初始化注册错误异常.

        Args:
            service_key: 服务键
            reason: 失败原因
        """
        self.reason = reason
        message = f"Failed to register service '{service_key}': {reason}"
        super().__init__(message, service_key)


class ResolutionError(ContainerException):
    """解析错误异常.

    当服务解析失败时抛出此异常.

    Attributes:
        message: 异常消息
        service_key: 相关的服务键
        original_exception: 原始异常
    """

    def __init__(
        self,
        service_key: ServiceKey,
        original_exception: Exception | None = None,
    ) -> None:
        """初始化解析错误异常.

        Args:
            service_key: 服务键
            original_exception: 原始异常
        """
        self.original_exception = original_exception
        message = f"Failed to resolve service '{service_key}'"
        if original_exception:
            message += f": {original_exception!s}"
        super().__init__(message, service_key)


class InvalidConfigurationError(ContainerException):
    """无效配置异常.

    当容器配置无效时抛出此异常.

    Examples:
        >>> container = Container(strict_mode=True, enable_auto_wiring=True)
        # strict_mode 和 enable_auto_wiring 不能同时为 True
        Traceback (most recent call last):
            ...
        InvalidConfigurationError: Incompatible configuration: ...
    """

    def __init__(self, message: str) -> None:
        """初始化无效配置异常.

        Args:
            message: 异常消息
        """
        super().__init__(f"Invalid configuration: {message}")


class OptionalDependencyError(ContainerException):
    """可选依赖错误异常.

    当处理可选依赖时出现错误时抛出此异常.

    Attributes:
        message: 异常消息
        service_key: 相关的服务键
        dependency_key: 可选依赖键
    """

    def __init__(
        self,
        service_key: ServiceKey,
        dependency_key: ServiceKey,
    ) -> None:
        """初始化可选依赖错误异常.

        Args:
            service_key: 服务键
            dependency_key: 可选依赖键
        """
        message = f"Failed to resolve optional dependency '{dependency_key}' for service '{service_key}'"
        super().__init__(message, service_key)


class ScopeNotActiveError(ContainerException):
    """作用域未激活异常.

    当在作用域外访问作用域内的服务时抛出此异常.

    Examples:
        >>> with container.create_scope() as scope:
        ...     service = scope.resolve(ScopedService)
        >>> # 现在作用域已离开
        >>> scope.resolve(ScopedService)  # 异常!
        Traceback (most recent call last):
            ...
        ScopeNotActiveError: Cannot resolve scoped service outside of scope
    """

    def __init__(self, message: str = "Scope is not active") -> None:
        """初始化作用域未激活异常.

        Args:
            message: 异常消息
        """
        super().__init__(message)


class InterceptorError(ContainerException):
    """拦截器错误异常.

    当拦截器执行出错时抛出此异常.

    Attributes:
        message: 异常消息
        service_key: 相关的服务键
        interceptor_name: 拦截器名称
        original_exception: 原始异常
    """

    def __init__(
        self,
        service_key: ServiceKey,
        interceptor_name: str,
        original_exception: Exception | None = None,
    ) -> None:
        """初始化拦截器错误异常.

        Args:
            service_key: 服务键
            interceptor_name: 拦截器名称
            original_exception: 原始异常
        """
        self.interceptor_name = interceptor_name
        self.original_exception = original_exception
        message = f"Interceptor '{interceptor_name}' failed for service '{service_key}'"
        if original_exception:
            message += f": {original_exception!s}"
        super().__init__(message, service_key)


class FactoryError(ContainerException):
    """工厂函数错误异常.

    当工厂函数执行出错时抛出此异常.

    Attributes:
        message: 异常消息
        service_key: 相关的服务键
        original_exception: 原始异常
    """

    def __init__(
        self,
        service_key: ServiceKey,
        original_exception: Exception | None = None,
    ) -> None:
        """初始化工厂函数错误异常.

        Args:
            service_key: 服务键
            original_exception: 原始异常
        """
        self.original_exception = original_exception
        message = f"Factory function for service '{service_key}' raised an exception"
        if original_exception:
            message += f": {original_exception!s}"
        super().__init__(message, service_key)
