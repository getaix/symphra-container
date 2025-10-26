"""核心容器模块.

提供了主要的依赖注入容器实现,支持:
- 4 种生命周期(Singleton, Transient, Scoped, Factory)
- 混合服务键模式(Type + String)
- 完整的类型提示支持
- 异步支持
- 拦截器系统
- 循环依赖检测

主要类:
  - ServiceRegistration: 服务注册信息
  - Container: 主容器类
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil
import uuid
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    overload,
    get_type_hints,
    get_origin,
    get_args,
)

from .circular import CircularDependencyDetector
from .circular import LazyProxy, LazyTypeMarker, Lazy
from .exceptions import (
    ContainerException,
    InvalidConfigurationError,
    RegistrationError,
    ResolutionError,
    ScopeNotActiveError,
    ServiceNotFoundError,
)
from .injector import ConstructorInjector, DependencyInfo
from .lifetime_manager import LifetimeManager
from .performance import PerformanceMetrics, ResolutionTimer
from .types import Lifetime, ServiceKey, InjectionMarker
from .decorators import get_service_metadata

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
S = TypeVar("S")


class ServiceRegistration:
    """服务注册信息.

    存储已注册服务的所有相关信息.

    Attributes:
        key: 服务键
        service_type: 服务类型
        factory: 工厂函数
        lifetime: 生命周期
        override: 是否覆盖已存在的服务
        is_async: 标记factory是否为异步函数
    """

    def __init__(
        self,
        key: ServiceKey,
        service_type: type,
        factory: Callable[..., Any] | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        override: bool = False,
    ) -> None:
        """初始化服务注册信息.

        Args:
            key: 服务键
            service_type: 服务类型
            factory: 工厂函数(可选)
            lifetime: 生命周期
            override: 是否覆盖已存在的服务
        """
        self.key = key
        self.service_type = service_type
        self.factory = factory
        self.lifetime = lifetime
        self.override = override
        # 自动检测factory是否为异步
        self.is_async = asyncio.iscoroutinefunction(factory) if factory else False

    @property
    def is_async_factory(self) -> bool:
        """检测factory是否为异步函数.

        Returns:
            True if factory is async, False otherwise
        """
        return self.is_async

    def __repr__(self) -> str:
        """返回字符串表示."""
        async_marker = " [async]" if self.is_async else ""
        return (
            f"ServiceRegistration(key={self.key}, "
            f"type={self.service_type.__name__}, "
            f"lifetime={self.lifetime.name}{async_marker})"
        )


class Container:
    """依赖注入容器.

    核心容器实现,提供了完整的依赖注入功能:
    - 服务注册和解析
    - 4 种生命周期管理
    - 依赖注入
    - 拦截器支持
    - 作用域管理
    - 循环依赖检测

    Attributes:
        _registrations: 服务注册字典
        _lifetime_manager: 生命周期管理器
        _interceptors: 拦截器字典
        _circular_detector: 循环依赖检测器
        _performance_metrics: 性能指标收集器
        _enable_performance_tracking: 是否启用性能跟踪
    """

    def __init__(
        self,
        enable_auto_wiring: bool = False,
        strict_mode: bool = False,
        enable_performance_tracking: bool = False,
    ) -> None:
        """初始化容器.

        Args:
            enable_auto_wiring: 是否启用自动装配
            strict_mode: 是否启用严格模式
            enable_performance_tracking: 是否启用性能跟踪

        Raises:
            InvalidConfigurationError: 配置无效时
        """
        # 检查配置有效性
        if enable_auto_wiring and strict_mode:
            msg = "Cannot enable both auto_wiring and strict_mode simultaneously"
            raise InvalidConfigurationError(
                msg,
            )

        self._registrations: dict[ServiceKey, ServiceRegistration] = {}
        self._lifetime_manager = LifetimeManager()
        self._interceptors: dict[str, list[Any]] = {
            "before": [],
            "after": [],
            "error": [],
        }
        self._circular_detector = CircularDependencyDetector()
        self._performance_metrics = PerformanceMetrics()
        self._enable_performance_tracking = enable_performance_tracking
        self.enable_auto_wiring = enable_auto_wiring
        self.strict_mode = strict_mode
        # 别名映射: 别名 -> 实际键
        self._aliases: dict[str, ServiceKey] = {}

    # ===================== 注册方法 =====================

    def register(
        self,
        service_type: type,
        *,
        key: ServiceKey | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        override: bool = False,
    ) -> Container:
        """注册一个服务.

        最基础的注册方法,使用服务类本身创建实例.

        Args:
            service_type: 服务类型
            key: 服务键(默认为 service_type)
            lifetime: 生命周期(默认 TRANSIENT)
            override: 是否覆盖已存在的服务

        Returns:
            容器实例(支持链式调用)

        Raises:
            RegistrationError: 注册失败时

        Examples:
            >>> container = Container()
            >>> container.register(UserService)
            >>> container.register(DatabaseService, lifetime=Lifetime.SINGLETON)
            >>> service = container.resolve(UserService)
        """
        # 如果服务类型带有装饰器元数据,优先使用元数据中的键与生命周期
        metadata = get_service_metadata(service_type)
        decorated_override = False
        if metadata is not None:
            # 使用装饰器提供的 key (如未显式传入)
            key = key or metadata.key or service_type
            # 使用装饰器提供的生命周期
            lifetime = metadata.lifetime
            # 对装饰过的服务默认允许重复注册(覆盖)
            decorated_override = True
        else:
            key = key or service_type

        # 检查是否已注册
        if key in self._registrations and not (override or decorated_override):
            raise RegistrationError(
                key,
                "Service already registered. Use override=True to replace it.",
            )

        registration = ServiceRegistration(
            key=key,
            service_type=service_type,
            factory=service_type,
            lifetime=lifetime,
            override=override or decorated_override,
        )
        self._registrations[key] = registration

        return self

    def register_instance(
        self,
        key: ServiceKey,
        instance: Any,
        override: bool = False,
    ) -> Container:
        """注册一个单例实例.

        直接注册一个已经创建的实例作为单例.

        Args:
            key: 服务键
            instance: 服务实例
            override: 是否覆盖已存在的服务

        Returns:
            容器实例(支持链式调用)

        Raises:
            RegistrationError: 注册失败时

        Examples:
            >>> config = Config()
            >>> container.register_instance("config", config)
            >>> resolved_config = container.resolve("config")
            >>> assert resolved_config is config
        """
        if key in self._registrations and not override:
            raise RegistrationError(
                key,
                "Service already registered. Use override=True to replace it.",
            )

        # 创建一个返回该实例的工厂
        def factory() -> Any:
            return instance

        registration = ServiceRegistration(
            key=key,
            service_type=type(instance),
            factory=factory,
            lifetime=Lifetime.SINGLETON,
            override=override,
        )
        self._registrations[key] = registration

        # 直接存储到单例存储
        self._lifetime_manager.set_instance(key, instance, Lifetime.SINGLETON)

        return self

    def register_factory(
        self,
        key: ServiceKey,
        factory: Callable[..., T],
        *,
        service_type: type | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        override: bool = False,
    ) -> Container:
        """注册一个工厂函数.

        使用工厂函数来创建服务实例.

        Args:
            key: 服务键
            factory: 工厂函数
            service_type: 服务类型(默认为工厂的返回类型)
            lifetime: 生命周期
            override: 是否覆盖已存在的服务

        Returns:
            容器实例(支持链式调用)

        Raises:
            RegistrationError: 注册失败时

        Examples:
            >>> def create_db() -> Database:
            ...     db = Database()
            ...     db.connect()
            ...     return db
            >>> container.register_factory(
            ...     "database",
            ...     create_db,
            ...     lifetime=Lifetime.SINGLETON
            ... )
        """
        if key in self._registrations and not override:
            raise RegistrationError(
                key,
                "Service already registered. Use override=True to replace it.",
            )

        service_type = service_type or type(None)

        registration = ServiceRegistration(
            key=key,
            service_type=service_type,
            factory=factory,
            lifetime=lifetime,
            override=override,
        )
        self._registrations[key] = registration

        return self

    def register_async_factory(
        self,
        key: ServiceKey,
        factory: Callable[..., T],
        *,
        service_type: type | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        override: bool = False,
    ) -> Container:
        """注册一个异步工厂函数.

        ⚠️ DEPRECATED: 此方法已废弃,请使用 register_factory() 代替。
        Container 现在自动检测工厂函数是否为异步。

        Args:
            key: 服务键
            factory: 异步工厂函数
            service_type: 服务类型
            lifetime: 生命周期
            override: 是否覆盖已存在的服务

        Returns:
            容器实例(支持链式调用)
        """
        # 直接调用 register_factory,它会自动检测异步
        return self.register_factory(
            key=key,
            factory=factory,
            service_type=service_type,
            lifetime=lifetime,
            override=override,
        )

    # ===================== 解析方法 =====================

    def _check_cached_instance(
        self,
        key: ServiceKey,
        registration: ServiceRegistration,
    ) -> tuple[Any | None, bool]:
        """检查缓存的实例.

        性能优化: 单例访问是最频繁的操作,优化此路径.

        Args:
            key: 服务键
            registration: 服务注册信息

        Returns:
            (实例, 是否命中缓存) 元组
        """
        # 性能优化: 单例是最常见的情况,直接访问字典避免函数调用开销
        if registration.lifetime == Lifetime.SINGLETON:
            # 直接从单例存储中获取,避免 get_instance 的额外开销
            cached = self._lifetime_manager._singleton_store.get(key)
            if cached is not None:
                return cached, True

        elif registration.lifetime == Lifetime.SCOPED:
            if self._lifetime_manager.has_active_scope():
                scope = self._lifetime_manager.current_scope
                if scope is not None:
                    cached = scope.get(key)
                    if cached is not None:
                        return cached, True

        return None, False

    async def _check_cached_instance_async(
        self,
        key: ServiceKey,
        registration: ServiceRegistration,
    ) -> tuple[Any | None, bool]:
        """异步检查缓存的实例.

        Args:
            key: 服务键
            registration: 服务注册信息

        Returns:
            (实例, 是否命中缓存) 元组
        """
        if registration.lifetime == Lifetime.SINGLETON:
            # 检查是否已有缓存
            cached = self._lifetime_manager._singleton_store.get(key)
            if cached is not None:
                return cached, True
            # 没有缓存,返回 None,由调用者创建并缓存
            return None, False

        if registration.lifetime == Lifetime.SCOPED and self._lifetime_manager.has_active_scope():
            scope = self._lifetime_manager.current_scope
            if scope is not None:
                cached = scope.get(key)
                if cached is not None:
                    return cached, True

        return None, False

    def _run_before_interceptors(self, key: ServiceKey, registration: ServiceRegistration) -> None:
        """运行前置拦截器.

        Args:
            key: 服务键
            registration: 服务注册信息

        Raises:
            ResolutionError: 拦截器拒绝解析时
        """
        for interceptor in self._interceptors["before"]:
            if not interceptor(key, registration):
                raise ResolutionError(key, Exception("前置拦截器拒绝了解析"))

    def _run_after_interceptors(self, key: ServiceKey, instance: Any) -> Any:
        """运行后置拦截器.

        Args:
            key: 服务键
            instance: 服务实例

        Returns:
            处理后的实例
        """
        result_instance = instance
        for interceptor in self._interceptors["after"]:
            result = interceptor(key, result_instance)
            if result is not None:
                result_instance = result
        return result_instance

    def _run_error_interceptors(self, key: ServiceKey, error: Exception) -> None:
        """运行错误拦截器.

        Args:
            key: 服务键
            error: 异常对象
        """
        for interceptor in self._interceptors["error"]:
            interceptor(key, error)

    @overload
    def resolve(self, key: type[T]) -> T: ...

    @overload
    def resolve(self, key: str) -> Any: ...

    def resolve(self, key: ServiceKey) -> Any:
        """解析服务实例.

        根据服务键从容器中获取服务实例. 这是整个 DI 容器最核心的方法,
        包含了完整的依赖解析、生命周期管理、拦截器执行和性能追踪逻辑.

        工作流程:
        1. 验证服务已注册
        2. 执行前置拦截器(可能拒绝解析)
        3. 初始化性能追踪(如果启用)
        4. 循环依赖检测
        5. 检查缓存实例(Singleton/Scoped)
        6. 创建新实例(递归解析依赖)
        7. 存储实例到生命周期管理器
        8. 执行后置拦截器并返回最终实例

        Args:
            key: 服务键(可以是类型或字符串)

        Returns:
            解析得到的服务实例

        Raises:
            ServiceNotFoundError: 服务未注册
            CircularDependencyError: 检测到循环依赖
            ResolutionError: 解析失败(依赖注入错误、工厂异常等)

        Examples:
            >>> container.register(UserService)
            >>> service = container.resolve(UserService)
            >>> assert isinstance(service, UserService)
        """
        # 步骤 0: 检查是否为别名, 如果是则转换为实际键
        if key in self._aliases:
            key = self._aliases[key]

        # Handle Lazy types
        origin = get_origin(key)
        if origin == LazyTypeMarker:
            args = get_args(key)
            if args:
                inner_key = args[0]
                return Lazy(inner_key, _resolver=self.resolve)
            else:
                raise ResolutionError(key, Exception("Lazy type must have arguments"))
        if key not in self._registrations:
            available_services = list(self._registrations.keys())
            raise ServiceNotFoundError(key, available_services)

        registration = self._registrations[key]

        # 检查是否尝试同步解析异步服务
        if registration.is_async:
            raise ResolutionError(
                key,
                Exception(f"Service {key} has async factory, use resolve_async() instead of resolve()"),
            )

        # 步骤 2: 执行前置拦截器(可能拒绝解析)
        self._run_before_interceptors(key, registration)

        # 步骤 3: 初始化性能追踪(如果启用)
        timer = ResolutionTimer() if self._enable_performance_tracking else None
        cache_hit = False

        try:
            # 开始计时
            if timer:
                timer.__enter__()

            # 步骤 4: 循环依赖检测 - 进入解析堆栈
            self._circular_detector.enter_resolution(key)

            # 步骤 5: 检查是否有缓存实例(Singleton/Scoped)
            cached, cache_hit = self._check_cached_instance(key, registration)
            if cached is not None:
                return cached

            # 步骤 6: 创建新实例(递归解析依赖)
            instance = self._create_instance(registration)

            # 步骤 7: 存储实例到生命周期管理器
            self._lifetime_manager.set_instance(key, instance, registration.lifetime)

            # 步骤 8: 执行后置拦截器并返回最终实例
            return self._run_after_interceptors(key, instance)

        except ContainerException:
            # 容器异常直接重新抛出
            raise
        except Exception as e:
            # 其他异常: 通知错误拦截器并包装为 ResolutionError
            self._run_error_interceptors(key, e)
            raise ResolutionError(key, e) from e
        finally:
            # 清理工作: 从循环检测堆栈中移除
            self._circular_detector.exit_resolution(key)

            # 记录性能指标(如果启用追踪)
            if timer:
                timer.__exit__(None, None, None)
                self._performance_metrics.record_resolution(
                    key,
                    timer.elapsed_time,
                    cache_hit=cache_hit,
                )

    @overload
    async def resolve_async(self, key: type[T]) -> T: ...

    @overload
    async def resolve_async(self, key: str) -> Any: ...

    async def resolve_async(self, key: ServiceKey) -> Any:
        """异步解析服务实例.

        与 resolve() 类似,但支持异步工厂函数和异步依赖解析.
        可以解析同步服务(自动适配)和异步服务.

        工作流程:
        1. 验证服务已注册
        2. 执行前置拦截器
        3. 初始化性能追踪
        4. 循环依赖检测
        5. 检查缓存实例
        6. 创建新实例(支持异步factory和依赖)
        7. 存储实例到生命周期管理器
        8. 执行后置拦截器并返回实例

        Args:
            key: 服务键(可以是类型或字符串)

        Returns:
            解析得到的服务实例

        Raises:
            ServiceNotFoundError: 服务未注册
            CircularDependencyError: 检测到循环依赖
            ResolutionError: 解析失败

        Examples:
            >>> container.register(AsyncService, factory=create_async_service)
            >>> service = await container.resolve_async(AsyncService)
            >>> assert isinstance(service, AsyncService)
        """
        # 步骤 0: 检查是否为别名
        if key in self._aliases:
            key = self._aliases[key]

        # Handle Lazy types
        origin = get_origin(key)
        if origin == LazyTypeMarker:
            args = get_args(key)
            if args:
                inner_key = args[0]
                return Lazy(inner_key, _resolver=self.resolve_async)
            else:
                raise ResolutionError(key, Exception("Lazy type must have arguments"))

        # 步骤 1: 验证服务已注册
        if key not in self._registrations:
            available_services = list(self._registrations.keys())
            raise ServiceNotFoundError(key, available_services)

        registration = self._registrations[key]

        # 步骤 2: 执行前置拦截器
        await self._run_before_interceptors_async(key, registration)

        # 步骤 3: 初始化性能追踪
        timer = ResolutionTimer() if self._enable_performance_tracking else None
        cache_hit = False

        try:
            if timer:
                timer.__enter__()

            # 步骤 4: 循环依赖检测
            self._circular_detector.enter_resolution(key)

            # 步骤 5: 检查缓存实例(异步版本)
            cached, cache_hit = await self._check_cached_instance_async(key, registration)
            if cached is not None:
                return cached

            # 步骤 6: 创建新实例(异步)
            instance = await self._create_instance_async(registration)

            # 步骤 7: 存储实例
            self._lifetime_manager.set_instance(key, instance, registration.lifetime)

            # 步骤 8: 执行后置拦截器
            return await self._run_after_interceptors_async(key, instance)

        except ContainerException:
            raise
        except Exception as e:
            await self._run_error_interceptors_async(key, e)
            raise ResolutionError(key, e) from e
        finally:
            self._circular_detector.exit_resolution(key)

            if timer:
                timer.__exit__(None, None, None)
                self._performance_metrics.record_resolution(
                    key,
                    timer.elapsed_time,
                    cache_hit=cache_hit,
                )

    def _analyze_service_dependencies(self, registration: ServiceRegistration) -> list[DependencyInfo]:
        """分析服务依赖.

        Args:
            registration: 服务注册信息

        Returns:
            依赖信息列表

        Raises:
            ResolutionError: 分析失败时
        """
        try:
            # 如果是工厂函数，分析其参数依赖
            if registration.factory is not None:
                return self._analyze_function_dependencies(registration.factory)
            # 否则按构造函数依赖分析
            return ConstructorInjector.analyze_dependencies(registration.service_type)
        except ResolutionError:
            raise
        except Exception as e:
            raise ResolutionError(registration.key, e) from e

    def _analyze_function_dependencies(self, func: Callable[..., Any]) -> list[DependencyInfo]:
        """分析工厂函数参数依赖.

        支持类型注解、Optional、默认值以及 Injected 标记。
        """
        dependencies: list[DependencyInfo] = []
        try:
            signature = inspect.signature(func)
            try:
                type_hints = get_type_hints(func)
            except Exception:  # noqa: BLE001
                type_hints = getattr(func, "__annotations__", {})

            for param_name, param in signature.parameters.items():
                # 跳过 *args/**kwargs 这类动态参数
                if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue

                # 检查 Injected 标记
                is_injected = isinstance(param.default, InjectionMarker)

                # 必须有类型注解才能进行依赖注入
                if param.annotation == inspect.Parameter.empty:
                    continue

                param_type = type_hints.get(param_name, param.annotation)

                # 简单类型直接跳过
                if ConstructorInjector._is_simple_type(param_type):
                    continue

                # 处理 Optional[T]
                is_optional, actual_type = ConstructorInjector._extract_optional_type(param_type)

                should_add = is_injected or param.default is inspect.Parameter.empty or is_optional
                if should_add:
                    dependencies.append(
                        DependencyInfo(
                            parameter_name=param_name,
                            service_key=actual_type,
                            service_type=actual_type,
                            is_optional=is_optional,
                            default_value=param.default,
                            is_injected=is_injected,
                        )
                    )

            return dependencies
        except Exception as e:  # noqa: BLE001
            raise ResolutionError(func, Exception(f"Failed to analyze factory dependencies: {e!s}")) from e

    def _resolve_dependencies(self, dependencies: list[DependencyInfo]) -> dict[str, Any]:
        """解析依赖参数.

        性能优化: 减少异常处理开销,大部分情况下依赖都能正常解析.

        Args:
            dependencies: 依赖信息列表

        Returns:
            参数名到实例的映射

        Raises:
            ServiceNotFoundError: 必需依赖未注册时
        """
        # 性能优化: 预分配字典大小
        kwargs: dict[str, Any] = {}

        # 性能优化: 快速路径 - 大部分服务没有依赖或依赖很少
        if not dependencies:
            return kwargs

        # 获取注册表引用,避免重复属性查找
        registrations = self._registrations

        for dep in dependencies:
            # 先规范化可能的字符串服务键到已注册类型(支持局部类/未来注解)
            if isinstance(dep.service_key, str):
                name = dep.service_key
                # 尝试别名匹配
                if name in self._aliases:
                    dep.service_key = self._aliases[name]
                    if isinstance(dep.service_key, type):
                        dep.service_type = dep.service_key
                else:
                    for registered_type in registrations.keys():
                        if isinstance(registered_type, type):
                            if (
                                registered_type.__name__ == name
                                or registered_type.__qualname__.split(".")[-1] == name
                            ):
                                dep.service_key = registered_type
                                dep.service_type = registered_type
                                break

            # 处理 Lazy[T] 依赖: 注入 LazyProxy, 延迟解析真实类型
            is_lazy = False
            inner_key = None
            
            # 检查 LazyTypeMarker 实例
            is_lazy_marker = (hasattr(dep.service_key, "inner_type") or
                             (hasattr(dep.service_key, "__class__") and
                              dep.service_key.__class__.__name__ == "LazyTypeMarker") or
                             hasattr(dep.service_type, "inner_type") or
                             (hasattr(dep.service_type, "__class__") and
                              dep.service_type.__class__.__name__ == "LazyTypeMarker"))
            
            if is_lazy_marker:
                is_lazy = True
                marker = dep.service_key if (hasattr(dep.service_key, "inner_type") or
                                            (hasattr(dep.service_key, "__class__") and
                                             dep.service_key.__class__.__name__ == "LazyTypeMarker")) else dep.service_type
                inner_key = marker.inner_type
            # 检查字符串形式的 Lazy[T]
            elif (isinstance(dep.service_key, str) and
                  dep.service_key.startswith("Lazy[") and
                  dep.service_key.endswith("]")):
                is_lazy = True
                inner_name = dep.service_key[5:-1]
                # 查找匹配的类型
                for registered_type in registrations:
                    if isinstance(registered_type, type) and (
                        registered_type.__name__ == inner_name or
                        registered_type.__qualname__.split(".")[-1] == inner_name
                    ):
                        inner_key = registered_type
                        break
                if inner_key is None and inner_name in self._aliases:
                    inner_key = self._aliases[inner_name]
            
            if is_lazy and inner_key is not None:                # 非可选依赖需要确保真实类型已注册
                if inner_key not in registrations:
                    if not dep.is_optional:
                        raise ServiceNotFoundError(inner_key)
                    # 可选依赖且未注册: 跳过注入
                    continue

                # 如果内部服务是异步的,使用异步解析工厂; 否则使用同步解析
                inner_reg = registrations.get(inner_key)
                if inner_reg is not None and inner_reg.is_async:
                    # 使用默认参数捕获 inner_key,避免闭包问题
                    kwargs[dep.parameter_name] = LazyProxy(lambda k=inner_key: self.resolve_async(k))
                else:
                    # 使用默认参数捕获 inner_key,避免闭包问题
                    kwargs[dep.parameter_name] = LazyProxy(lambda k=inner_key: self.resolve(k))
                continue

            # 常规依赖解析路径
            if dep.service_key not in registrations:
                if not dep.is_optional:
                    raise ServiceNotFoundError(dep.service_key)
                continue

            try:
                kwargs[dep.parameter_name] = self.resolve(dep.service_key)
            except Exception:
                if not dep.is_optional:
                    raise
        return kwargs

    def _invoke_factory(self, registration: ServiceRegistration, kwargs: dict[str, Any]) -> Any:
        """调用工厂创建实例.

        Args:
            registration: 服务注册信息
            kwargs: 构造参数

        Returns:
            创建的实例

        Raises:
            ResolutionError: 工厂调用失败时
        """
        factory = registration.factory
        if factory is None:
            raise ResolutionError(registration.key, Exception("No factory defined"))

        try:
            if callable(factory):
                return factory(**kwargs)
            raise ResolutionError(registration.key, Exception("Factory is not callable"))
        except ResolutionError:
            raise
        except Exception as e:
            raise ResolutionError(registration.key, e) from e

    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """创建服务实例.

        根据注册信息创建一个新实例.

        Args:
            registration: 服务注册信息

        Returns:
            创建的实例

        Raises:
            ResolutionError: 创建失败时
        """
        # 分析依赖
        dependencies = self._analyze_service_dependencies(registration)

        # 解析依赖
        kwargs = self._resolve_dependencies(dependencies)

        # 调用工厂创建实例
        return self._invoke_factory(registration, kwargs)

    async def _resolve_dependencies_async(self, dependencies: list[DependencyInfo]) -> dict[str, Any]:
        """异步解析依赖参数.

        Args:
            dependencies: 依赖信息列表

        Returns:
            参数名到实例的映射

        Raises:
            ServiceNotFoundError: 必需依赖未注册时
        """
        kwargs: dict[str, Any] = {}
        registrations = self._registrations
        for dep in dependencies:
            # 先规范化可能的字符串服务键到已注册类型(支持局部类/未来注解)
            if isinstance(dep.service_key, str):
                name = dep.service_key
                if name in self._aliases:
                    dep.service_key = self._aliases[name]
                    if isinstance(dep.service_key, type):
                        dep.service_type = dep.service_key
                else:
                    for registered_type in registrations.keys():
                        if isinstance(registered_type, type):
                            if (
                                registered_type.__name__ == name
                                or registered_type.__qualname__.split(".")[-1] == name
                            ):
                                dep.service_key = registered_type
                                dep.service_type = registered_type
                                break

            # 处理 Lazy[T] 依赖: 在异步上下文中注入 LazyProxy
            is_lazy = False
            inner_key = None
            
            # 检查 LazyTypeMarker 实例
            is_lazy_marker = (hasattr(dep.service_key, "inner_type") or
                             (hasattr(dep.service_key, "__class__") and
                              dep.service_key.__class__.__name__ == "LazyTypeMarker") or
                             hasattr(dep.service_type, "inner_type") or
                             (hasattr(dep.service_type, "__class__") and
                              dep.service_type.__class__.__name__ == "LazyTypeMarker"))
            
            if is_lazy_marker:
                is_lazy = True
                marker = dep.service_key if (hasattr(dep.service_key, "inner_type") or
                                            (hasattr(dep.service_key, "__class__") and
                                             dep.service_key.__class__.__name__ == "LazyTypeMarker")) else dep.service_type
                inner_key = marker.inner_type
            # 检查字符串形式的 Lazy[T]
            elif (isinstance(dep.service_key, str) and
                  dep.service_key.startswith("Lazy[") and
                  dep.service_key.endswith("]")):
                is_lazy = True
                inner_name = dep.service_key[5:-1]
                # 查找匹配的类型
                for registered_type in registrations:
                    if isinstance(registered_type, type) and (
                        registered_type.__name__ == inner_name or
                        registered_type.__qualname__.split(".")[-1] == inner_name
                    ):
                        inner_key = registered_type
                        break
                if inner_key is None and inner_name in self._aliases:
                    inner_key = self._aliases[inner_name]
            
            if is_lazy and inner_key is not None:

                # 非可选依赖需要确保真实类型已注册
                if inner_key not in registrations:
                    if not dep.is_optional:
                        raise ServiceNotFoundError(inner_key)
                    # 可选依赖且未注册: 跳过注入
                    continue

                # 如果内部服务是异步的,使用异步解析工厂; 否则使用同步解析
                inner_reg = registrations.get(inner_key)
                if inner_reg is not None and inner_reg.is_async:
                    # 使用默认参数捕获 inner_key,避免闭包问题
                    kwargs[dep.parameter_name] = LazyProxy(lambda k=inner_key: self.resolve_async(k))
                else:
                    # 使用默认参数捕获 inner_key,避免闭包问题
                    kwargs[dep.parameter_name] = LazyProxy(lambda k=inner_key: self.resolve(k))
                continue

            # 常规依赖解析路径
            if dep.service_key not in registrations:
                if not dep.is_optional:
                    raise ServiceNotFoundError(dep.service_key)
                continue

            try:
                # 在异步上下文中,总是使用异步解析
                kwargs[dep.parameter_name] = await self.resolve_async(dep.service_key)
            except Exception:
                if not dep.is_optional:
                    raise
        return kwargs

    async def _invoke_factory_async(self, registration: ServiceRegistration, kwargs: dict[str, Any]) -> Any:
        """异步调用工厂创建实例.

        Args:
            registration: 服务注册信息
            kwargs: 构造参数

        Returns:
            创建的实例

        Raises:
            ResolutionError: 工厂调用失败时
        """
        factory = registration.factory
        if factory is None:
            raise ResolutionError(registration.key, Exception("No factory defined"))

        try:
            if callable(factory):
                if registration.is_async:
                    # 异步工厂
                    return await factory(**kwargs)
                # 同步工厂也可以在异步中调用
                return factory(**kwargs)
            raise ResolutionError(registration.key, Exception("Factory is not callable"))
        except ResolutionError:
            raise
        except Exception as e:
            raise ResolutionError(registration.key, e) from e

    async def _create_instance_async(self, registration: ServiceRegistration) -> Any:
        """异步创建服务实例.

        根据注册信息创建一个新实例,支持异步factory和异步依赖.

        Args:
            registration: 服务注册信息

        Returns:
            创建的实例

        Raises:
            ResolutionError: 创建失败时
        """
        # 分析依赖
        dependencies = self._analyze_service_dependencies(registration)

        # 异步解析依赖
        kwargs = await self._resolve_dependencies_async(dependencies)

        # 异步调用工厂创建实例
        return await self._invoke_factory_async(registration, kwargs)

    async def _run_before_interceptors_async(self, key: ServiceKey, registration: ServiceRegistration) -> None:
        """异步执行前置拦截器."""
        for interceptor in self._interceptors["before"]:
            if inspect.iscoroutinefunction(interceptor):
                await interceptor(key, registration)
            else:
                interceptor(key, registration)

    async def _run_after_interceptors_async(self, key: ServiceKey, instance: Any) -> Any:
        """异步执行后置拦截器."""
        result = instance
        for interceptor in self._interceptors["after"]:
            if inspect.iscoroutinefunction(interceptor):
                result = await interceptor(key, result) or result
            else:
                result = interceptor(key, result) or result
        return result

    async def _run_error_interceptors_async(self, key: ServiceKey, error: Exception) -> None:
        """异步执行错误拦截器."""
        for interceptor in self._interceptors["error"]:
            if inspect.iscoroutinefunction(interceptor):
                await interceptor(key, error)
            else:
                interceptor(key, error)

    # ===================== 作用域方法 =====================

    def try_resolve(self, key: ServiceKey, default: T | None = None) -> T | None:
        """尝试解析服务,失败返回默认值.

        Args:
            key: 服务键
            default: 失败时的默认值

        Returns:
            服务实例或默认值

        Examples:
            >>> service = container.try_resolve(OptionalService)
            >>> if service is None:
            ...     print("Service not found")
        """
        try:
            return self.resolve(key)  # type: ignore[return-value]
        except (ServiceNotFoundError, ResolutionError):
            return default

    async def try_resolve_async(self, key: ServiceKey, default: T | None = None) -> T | None:
        """异步尝试解析服务,失败返回默认值.

        Args:
            key: 服务键
            default: 失败时的默认值

        Returns:
            服务实例或默认值

        Examples:
            >>> service = await container.try_resolve_async(OptionalService)
            >>> if service is None:
            ...     print("Service not found")
        """
        try:
            return await self.resolve_async(key)  # type: ignore[return-value]
        except (ServiceNotFoundError, ResolutionError):
            return default

    def unregister(self, key: ServiceKey) -> bool:
        """删除服务注册.

        Args:
            key: 服务键

        Returns:
            是否成功删除

        Examples:
            >>> container.register(Service)
            >>> container.unregister(Service)
            True
        """
        # 解析别名
        actual_key = self._aliases.get(key, key) if isinstance(key, str) else key

        if actual_key in self._registrations:
            del self._registrations[actual_key]
            # 清理该服务的实例
            self._lifetime_manager.remove_instance(actual_key)
            return True
        return False

    def clear(self, lifetime: Lifetime | None = None) -> None:
        """清空容器中的服务.

        Args:
            lifetime: 可选,仅清空指定生命周期的服务

        Examples:
            >>> container.clear()  # 清空所有
            >>> container.clear(Lifetime.TRANSIENT)  # 仅清空 Transient
        """
        if lifetime is None:
            # 清空所有
            self._registrations.clear()
            self._aliases.clear()
            self._lifetime_manager.clear()
        else:
            # 清空指定生命周期
            to_remove = [key for key, reg in self._registrations.items() if reg.lifetime == lifetime]
            for key in to_remove:
                self.unregister(key)

    def replace(self, old_key: ServiceKey, new_service_type: type) -> None:
        """替换已注册的服务.

        Args:
            old_key: 旧服务键
            new_service_type: 新服务类型

        Raises:
            ServiceNotFoundError: 旧服务不存在时

        Examples:
            >>> container.replace(OldService, NewService)
        """
        if old_key not in self._registrations:
            raise ServiceNotFoundError(old_key, list(self._registrations.keys()))

        old_reg = self._registrations[old_key]
        self.unregister(old_key)
        self.register(
            new_service_type,
            key=old_key,
            lifetime=old_reg.lifetime,
            override=True,
        )

    def has(self, key: ServiceKey) -> bool:
        """检查服务是否已注册(is_registered的别名).

        Args:
            key: 服务键

        Returns:
            是否已注册

        Examples:
            >>> container.has(UserService)
            True
        """
        return self.is_registered(key)

    def alias(self, key: ServiceKey, alias: str) -> Container:
        """为服务创建别名.

        Args:
            key: 原始服务键
            alias: 别名

        Returns:
            容器实例(支持链式调用)

        Raises:
            ServiceNotFoundError: 服务不存在时

        Examples:
            >>> container.alias(DatabaseService, "db")
            >>> db = container.resolve("db")
        """
        if key not in self._registrations:
            raise ServiceNotFoundError(key, list(self._registrations.keys()))

        self._aliases[alias] = key
        return self

    def scan(self, package: str | Path) -> Container:
        """扫描包并自动注册所有带装饰器的服务.

        Args:
            package: 包名或路径

        Returns:
            容器实例(支持链式调用)

        Examples:
            >>> container.scan("myapp.services")
            >>> container.scan(Path("./services"))
        """
        import contextlib

        from .decorators import auto_register, is_injectable

        if isinstance(package, Path):
            # 路径扫描
            package_str = str(package.absolute())
            spec = importlib.util.spec_from_file_location("__scan_module__", package_str)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for name in dir(module):
                    obj = getattr(module, name)
                    if is_injectable(obj):
                        auto_register(self, obj)
        else:
            # 包名扫描
            with contextlib.suppress(ImportError):
                module = importlib.import_module(package)
                for _, name, _ in pkgutil.walk_packages(
                    module.__path__,
                    prefix=f"{package}.",
                ):
                    with contextlib.suppress(ImportError, AttributeError):
                        sub_module = importlib.import_module(name)
                        for attr_name in dir(sub_module):
                            obj = getattr(sub_module, attr_name)
                            if is_injectable(obj):
                                auto_register(self, obj)

        return self

    def warmup(self, *keys: ServiceKey) -> None:
        """预热服务,提前创建单例实例.

        Args:
            *keys: 要预热的服务键,不提供则预热所有单例

        Examples:
            >>> container.warmup(DatabaseService, CacheService)
            >>> container.warmup()  # 预热所有单例
        """
        import contextlib

        if not keys:
            # 预热所有单例
            keys = tuple(key for key, reg in self._registrations.items() if reg.lifetime == Lifetime.SINGLETON)

        for key in keys:
            # 预热失败不影响后续服务
            with contextlib.suppress(ContainerException, ResolutionError):
                self.resolve(key)

    async def warmup_async(self, *keys: ServiceKey) -> None:
        """异步预热服务,提前创建单例实例.

        Args:
            *keys: 要预热的服务键,不提供则预热所有单例

        Examples:
            >>> await container.warmup_async(DatabaseService, CacheService)
            >>> await container.warmup_async()  # 预热所有单例
        """
        import contextlib

        if not keys:
            # 预热所有单例
            keys = tuple(key for key, reg in self._registrations.items() if reg.lifetime == Lifetime.SINGLETON)

        for key in keys:
            # 预热失败不影响后续服务
            with contextlib.suppress(ContainerException, ResolutionError):
                await self.resolve_async(key)

    def __getitem__(self, key: ServiceKey) -> Any:
        """简写语法: container[Service].

        Args:
            key: 服务键

        Returns:
            服务实例

        Examples:
            >>> service = container[UserService]
        """
        return self.resolve(key)

    def __setitem__(self, key: ServiceKey, value: Any) -> None:
        """简写语法: container["key"] = instance.

        Args:
            key: 服务键
            value: 服务实例或类型

        Examples:
            >>> container["config"] = config_obj
            >>> container[IService] = ServiceImpl
        """
        if isinstance(value, type):
            self.register(value, key=key, override=True)
        else:
            self.register_instance(key, value, override=True)

    # ===================== 作用域方法 =====================

    def create_scope(self) -> Scope:
        """创建新的作用域.

        用于管理 SCOPED 生命周期的服务.

        Returns:
            作用域上下文管理器

        Examples:
            >>> with container.create_scope() as scope:
            ...     service = scope.resolve(ScopedService)
            ...     # 在作用域内使用服务
        """
        return Scope(self)

    # ===================== 拦截器方法 =====================

    def add_interceptor(
        self,
        interceptor_type: str,
        interceptor: Any,
    ) -> Container:
        """添加拦截器.

        支持 "before", "after", "error" 三种类型.

        Args:
            interceptor_type: 拦截器类型
            interceptor: 拦截器函数

        Returns:
            容器实例(支持链式调用)

        Raises:
            ValueError: 拦截器类型无效时

        Examples:
            >>> def log_before(key, registration):
            ...     print(f"解析: {key}")
            ...     return True
            >>> container.add_interceptor("before", log_before)
        """
        if interceptor_type not in self._interceptors:
            msg = f"Invalid interceptor type: {interceptor_type}"
            raise ValueError(msg)

        self._interceptors[interceptor_type].append(interceptor)
        return self

    # ===================== 工具方法 =====================

    def is_registered(self, key: ServiceKey) -> bool:
        """检查服务是否已注册.

        Args:
            key: 服务键或别名

        Returns:
            是否已注册
        """
        return key in self._registrations or key in self._aliases

    def get_registration(self, key: ServiceKey) -> ServiceRegistration | None:
        """获取服务注册信息.

        Args:
            key: 服务键

        Returns:
            注册信息或 None
        """
        return self._registrations.get(key)

    def get_all_registrations(self) -> dict[ServiceKey, ServiceRegistration]:
        """获取所有注册信息.

        Returns:
            所有注册信息的字典
        """
        return self._registrations.copy()

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计信息.

        返回容器的性能指标,包括解析次数,缓存命中率等.

        Returns:
            包含性能指标的字典

        Examples:
            >>> container = Container(enable_performance_tracking=True)
            >>> container.register(UserService)
            >>> container.resolve(UserService)
            >>> stats = container.get_performance_stats()
            >>> print(f"Total resolutions: {stats['total_resolutions']}")
        """
        return self._performance_metrics.get_stats()

    def reset_performance_metrics(self) -> None:
        """重置性能指标.

        清空所有已记录的性能数据.
        """
        self._performance_metrics.reset()

    def dispose(self) -> None:
        """释放容器及其所有资源.

        包括单例实例,作用域等.
        """
        self._lifetime_manager.dispose_all()
        self._registrations.clear()
        self._interceptors.clear()
        self._circular_detector.reset()
        self._performance_metrics.reset()

    def __enter__(self) -> Container:
        """支持上下文管理器协议."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """离开上下文时释放资源."""
        self.dispose()

    async def __aenter__(self) -> Container:
        """支持异步上下文管理器协议."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """离开异步上下文时释放资源."""
        self.dispose()


class Scope:
    """作用域上下文管理器.

    用于管理 SCOPED 生命周期的服务.在进入作用域时创建,
    离开作用域时释放所有资源.

    Attributes:
        _container: 关联的容器
        _scope_id: 作用域 ID
    """

    def __init__(self, container: Container) -> None:
        """初始化作用域.

        Args:
            container: 关联的容器
        """
        self._container = container
        self._scope_id = str(uuid.uuid4())

    def __enter__(self) -> Scope:
        """进入作用域."""
        self._container._lifetime_manager.enter_scope(self._scope_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """离开作用域."""
        self._container._lifetime_manager.exit_scope(self._scope_id)

    def dispose(self) -> None:
        """手动释放作用域资源.

        与 __exit__ 相同,用于手动清理作用域资源.
        """
        self._container._lifetime_manager.exit_scope(self._scope_id)

    def resolve(self, key: ServiceKey) -> Any:
        """在当前作用域内解析服务.

        Args:
            key: 服务键

        Returns:
            服务实例

        Raises:
            ScopeNotActiveError: 作用域不活跃时
        """
        if not self._container._lifetime_manager.has_active_scope():
            msg = "Cannot resolve scoped service outside of scope"
            raise ScopeNotActiveError(msg)

        return self._container.resolve(key)
