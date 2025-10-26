"""依赖注入器模块.

负责分析服务类的构造函数,提取依赖关系,
并为容器解析服务时提供所需的依赖.

主要类:
  - DependencyInfo: 依赖信息
  - ConstructorInjector: 构造函数注入器
"""

from __future__ import annotations

import inspect
import types
from typing import Any, Union, get_args, get_origin, get_type_hints

from .exceptions import ResolutionError
from .types import InjectionMarker, ServiceKey


class DependencyInfo:
    """依赖信息.

    存储单个依赖的相关信息.

    Attributes:
        parameter_name: 参数名称
        service_key: 服务键(类型或字符串)
        service_type: 服务类型
        is_optional: 是否可选
        default_value: 默认值
        is_injected: 是否使用 Injected 标记
    """

    def __init__(
        self,
        parameter_name: str,
        service_key: ServiceKey,
        service_type: type,
        is_optional: bool = False,
        default_value: Any = inspect.Parameter.empty,
        is_injected: bool = False,
    ) -> None:
        """初始化依赖信息.

        Args:
            parameter_name: 参数名称
            service_key: 服务键
            service_type: 服务类型
            is_optional: 是否可选
            default_value: 默认值
            is_injected: 是否使用 Injected 标记
        """
        self.parameter_name = parameter_name
        self.service_key = service_key
        self.service_type = service_type
        self.is_optional = is_optional
        self.default_value = default_value
        self.is_injected = is_injected

    def __repr__(self) -> str:
        """返回字符串表示."""
        optional_str = " (optional)" if self.is_optional else ""
        injected_str = " (injected)" if self.is_injected else ""
        return f"DependencyInfo({self.parameter_name}: {self.service_key}{optional_str}{injected_str})"


class ConstructorInjector:
    """构造函数注入器.

    分析服务类的构造函数,提取依赖关系,
    为容器解析服务时提供依赖.

    Methods:
        analyze_dependencies: 分析构造函数依赖
        can_construct: 检查是否可以构建实例
        get_dependencies: 获取依赖列表
    """

    # 类级别的依赖分析缓存 - 大幅提升重复解析性能
    _dependency_cache: dict[type, list[DependencyInfo]] = {}

    @classmethod
    def clear_cache(cls) -> None:
        """清空依赖分析缓存.

        在测试或动态加载类时可能需要清空缓存.
        """
        cls._dependency_cache.clear()

    @staticmethod
    def _get_type_hints_safe(obj: Any) -> dict[str, Any]:
        """安全获取类型提示信息.

        Args:
            obj: 目标对象(类或函数)

        Returns:
            类型提示字典
        """
        try:
            # 获取对象的模块命名空间用于解析字符串注解
            globalns = getattr(obj, "__globals__", None)
            if globalns is None and hasattr(obj, "__module__"):
                import sys
                module = sys.modules.get(obj.__module__)
                if module:
                    globalns = vars(module)

            # 如果有模块命名空间,传递给 get_type_hints
            if globalns:
                return get_type_hints(obj, globalns=globalns)
            else:
                return get_type_hints(obj)
        except Exception:  # noqa: BLE001
            return getattr(obj, "__annotations__", {})

    @staticmethod
    def _is_simple_type(param_type: type) -> bool:
        """检查是否是简单类型.

        Args:
            param_type: 参数类型

        Returns:
            是否为简单类型
        """
        simple_types = (str, int, bool, float, bytes, list, dict, set, tuple, type(None))
        return param_type in simple_types

    @staticmethod
    def _extract_optional_type(param_type: Any) -> tuple[bool, Any]:
        """提取可选类型.

        Args:
            param_type: 参数类型

        Returns:
            (是否可选, 实际类型) 元组
        """
        origin = get_origin(param_type)
        is_union_type = origin is Union or isinstance(param_type, types.UnionType)

        if is_union_type:
            args = get_args(param_type)
            if type(None) in args:
                non_none_types = [arg for arg in args if arg is not type(None)]
                if non_none_types:
                    return True, non_none_types[0]

        return False, param_type

    @staticmethod
    def analyze_dependencies(service_class: type) -> list[DependencyInfo]:
        """分析服务类的构造函数依赖.

        通过检查 __init__ 方法的参数,提取所有依赖关系.
        支持以下特性:
        - 类型注解依赖
        - 可选依赖(Optional[T])
        - 默认值
        - Injected 标记

        性能优化: 使用类级别缓存,避免重复分析相同的类.

        Args:
            service_class: 服务类

        Returns:
            依赖信息列表

        Raises:
            ResolutionError: 无法分析依赖时

        Examples:
            >>> class UserService:
            ...     def __init__(self, repo: UserRepository):
            ...         self.repo = repo
            >>> deps = ConstructorInjector.analyze_dependencies(UserService)
            >>> assert len(deps) == 1
            >>> assert deps[0].service_key == UserRepository
        """
        # 性能优化: 检查缓存,避免重复分析
        if service_class in ConstructorInjector._dependency_cache:
            return ConstructorInjector._dependency_cache[service_class]

        dependencies: list[DependencyInfo] = []

        try:
            # 步骤 1: 获取构造函数签名
            init_method = service_class.__init__
            signature = inspect.signature(init_method)

            # 步骤 2: 安全获取类型提示信息
            type_hints = ConstructorInjector._get_type_hints_safe(init_method)

            # 步骤 3: 遍历所有参数进行依赖分析
            for param_name, param in signature.parameters.items():
                # 跳过 self 参数
                if param_name == "self":
                    continue

                # 检查是否使用了显式的 Injected 标记
                is_injected = isinstance(param.default, InjectionMarker)

                # 必须有类型注解才能进行依赖注入
                if param.annotation == inspect.Parameter.empty:
                    continue

                # 获取参数的实际类型
                param_type = type_hints.get(param_name, param.annotation)

                # 过滤掉基础数据类型(它们不需要注入)
                if ConstructorInjector._is_simple_type(param_type):
                    continue

                # 处理可选类型并提取真实类型
                is_optional, actual_type = ConstructorInjector._extract_optional_type(param_type)

                # 判断是否应该添加此依赖:
                # 1. 显式标记了 Injected
                # 2. 没有默认值(必需参数)
                # 3. 是可选类型(Optional[T])
                should_add = is_injected or param.default is inspect.Parameter.empty or is_optional
                if should_add:
                    # 创建依赖信息对象
                    dependency = DependencyInfo(
                        parameter_name=param_name,
                        service_key=actual_type,
                        service_type=actual_type,
                        is_optional=is_optional,
                        default_value=param.default,
                        is_injected=is_injected,
                    )
                    dependencies.append(dependency)

            # 性能优化: 缓存分析结果
            ConstructorInjector._dependency_cache[service_class] = dependencies
            return dependencies

        except ResolutionError:
            # 重新抛出已知的解析错误
            raise
        except Exception as e:
            # 将未知异常包装为 ResolutionError
            raise ResolutionError(
                service_class,
                Exception(f"Failed to analyze dependencies: {e!s}"),
            ) from e

    @staticmethod
    def can_construct(
        service_class: type,
        available_keys: set[ServiceKey],
    ) -> bool:
        """检查是否可以构建服务实例.

        通过检查所有依赖是否都在可用的服务键中,
        判断是否能够成功构建实例.

        Args:
            service_class: 服务类
            available_keys: 可用的服务键集合

        Returns:
            是否可以构建
        """
        dependencies = ConstructorInjector.analyze_dependencies(service_class)

        return all(not (not dep.is_optional and dep.service_key not in available_keys) for dep in dependencies)

    @staticmethod
    def get_dependencies(service_class: type) -> dict[str, DependencyInfo]:
        """获取依赖字典.

        以参数名为键,依赖信息为值的字典形式返回依赖.

        Args:
            service_class: 服务类

        Returns:
            依赖字典
        """
        dependencies = ConstructorInjector.analyze_dependencies(service_class)
        return {dep.parameter_name: dep for dep in dependencies}
