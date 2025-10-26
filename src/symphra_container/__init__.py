"""Symphra Container - 企业级 Python 依赖注入容器.

一个高性能,高可维护性,高扩展性的依赖注入容器库.

主要特性:
  - 4 种生命周期支持(Singleton, Transient, Scoped, Factory)
  - 混合服务键模式(Type + String)
  - 完整的类型提示支持
  - 异步支持
  - 拦截器系统
  - 循环依赖检测
  - 作用域管理
  - 资源释放管理

快速开始:

    >>> from symphra_container import Container, Lifetime, Injected
    >>>
    >>> # 创建容器
    >>> container = Container()
    >>>
    >>> # 注册服务
    >>> class UserService:
    ...     pass
    >>>
    >>> container.register(UserService, lifetime=Lifetime.SINGLETON)
    >>>
    >>> # 解析服务
    >>> service = container.resolve(UserService)

完整文档见: https://getaix.github.io/symphra-container
"""

from .circular import CircularDependencyDetector, Lazy, LazyProxy
from .container import Container, Scope, ServiceRegistration
from .decorators import (
    ServiceMetadata,
    auto_register,
    factory,
    get_service_metadata,
    injectable,
    is_injectable,
    scoped,
    singleton,
    transient,
)
from .exceptions import (
    CircularDependencyError,
    ContainerException,
    FactoryError,
    InterceptorError,
    InvalidConfigurationError,
    OptionalDependencyError,
    RegistrationError,
    ResolutionError,
    ScopeNotActiveError,
    ServiceNotFoundError,
    TypeMismatchError,
)
from .generics import GenericKey, is_generic_type, register_generic, resolve_generic
from .injector import ConstructorInjector, DependencyInfo
from .lifetime_manager import LifetimeManager, ScopedStore, SingletonStore
from .performance import (
    PerformanceMetrics,
    ResolutionTimer,
    ServiceKeyIndex,
)
from .types import (
    AsyncDisposable,
    Disposable,
    Injected,
    InjectionMarker,
    Lifetime,
    ServiceKey,
)
from .visualization import (
    ContainerDiagnostic,
    debug_resolution,
    diagnose_container,
    print_dependency_graph,
    visualize_container,
)

# 为了向后兼容, AsyncContainer 作为 Container 的别名
# ⚠️ DEPRECATED: 请直接使用 Container, 它现在同时支持同步和异步
AsyncContainer = Container

__version__ = "0.1.0"
__author__ = "Symphra Team"
__license__ = "MIT"

__all__ = [
    "AsyncContainer",  # 保留以向后兼容
    "AsyncDisposable",
    # Circular Dependency Handling
    "CircularDependencyDetector",
    "CircularDependencyError",
    # Dependency Injection
    "ConstructorInjector",
    # Core API
    "Container",
    "ContainerDiagnostic",
    # Exceptions
    "ContainerException",
    "DependencyInfo",
    "Disposable",
    "FactoryError",
    # Generics Support
    "GenericKey",
    "Injected",
    "InjectionMarker",
    "InterceptorError",
    "InvalidConfigurationError",
    "Lazy",
    "LazyProxy",
    # Types and Enums
    "Lifetime",
    # Lifetime Management
    "LifetimeManager",
    "OptionalDependencyError",
    # Performance Monitoring
    "PerformanceMetrics",
    "RegistrationError",
    "ResolutionError",
    "ResolutionTimer",
    "Scope",
    "ScopeNotActiveError",
    "ScopedStore",
    "ServiceKey",
    "ServiceKeyIndex",
    "ServiceMetadata",
    "ServiceNotFoundError",
    "ServiceRegistration",
    "SingletonStore",
    "TypeMismatchError",
    "auto_register",
    # Visualization & Debugging
    "debug_resolution",
    "diagnose_container",
    "factory",
    "get_service_metadata",
    # Decorators
    "injectable",
    "is_generic_type",
    "is_injectable",
    "print_dependency_graph",
    "register_generic",
    "resolve_generic",
    "scoped",
    "singleton",
    "transient",
    "visualize_container",
]
