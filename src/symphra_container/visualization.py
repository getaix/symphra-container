"""可视化和调试工具.

提供容器服务依赖关系的可视化、调试信息输出和诊断功能。

示例:
    >>> from symphra_container import Container
    >>> from symphra_container.visualization import (
    ...     visualize_container,
    ...     print_dependency_graph,
    ...     debug_resolution,
    ...     diagnose_container
    ... )
    >>>
    >>> container = Container()
    >>> # ... 注册服务 ...
    >>>
    >>> # 生成 DOT 格式的依赖图
    >>> dot = visualize_container(container)
    >>>
    >>> # 打印文本格式的依赖树
    >>> print_dependency_graph(container)
    >>>
    >>> # 调试服务解析过程
    >>> debug_resolution(container, UserService)
    >>>
    >>> # 诊断容器健康状态
    >>> report = diagnose_container(container)
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from symphra_container.container import Container

__all__ = [
    "ContainerDiagnostic",
    "debug_resolution",
    "diagnose_container",
    "print_dependency_graph",
    "visualize_container",
]


@dataclass
class ContainerDiagnostic:
    """容器诊断报告.

    Attributes:
        total_services: 总服务数
        singleton_count: 单例服务数
        transient_count: 瞬态服务数
        scoped_count: 作用域服务数
        circular_dependencies: 循环依赖列表
        unresolvable_services: 无法解析的服务列表
        warnings: 警告信息列表
        health_score: 健康评分 (0-100)
    """

    total_services: int
    singleton_count: int
    transient_count: int
    scoped_count: int
    circular_dependencies: list[tuple[Any, Any]]
    unresolvable_services: list[Any]
    warnings: list[str]
    health_score: float


def visualize_container(container: Container, format: str = "dot") -> str:
    """生成容器服务依赖关系的可视化图.

    Args:
        container: 容器实例
        format: 输出格式, 支持 'dot' (Graphviz) 或 'mermaid'

    Returns:
        可视化图的字符串表示

    Example:
        >>> dot = visualize_container(container, format='dot')
        >>> # 保存为文件供 Graphviz 渲染
        >>> with open('container.dot', 'w') as f:
        ...     f.write(dot)
        >>>
        >>> # 或者使用 Mermaid
        >>> mermaid = visualize_container(container, format='mermaid')
    """
    if format == "dot":
        return _generate_dot(container)
    if format == "mermaid":
        return _generate_mermaid(container)
    msg = f"Unsupported format: {format}"
    raise ValueError(msg)


def _generate_dot(container: Container) -> str:
    """生成 Graphviz DOT 格式."""
    from .types import Lifetime

    lines = ["digraph Container {", "  rankdir=LR;", "  node [shape=box];", ""]

    # 遍历所有注册的服务
    registrations = container._registrations

    for key, registration in registrations.items():
        key_name = _format_key(key)

        # 节点样式根据生命周期着色
        color = {
            Lifetime.SINGLETON: "lightblue",
            Lifetime.TRANSIENT: "lightgreen",
            Lifetime.SCOPED: "lightyellow",
        }.get(registration.lifetime, "white")

        lines.append(f'  "{key_name}" [style=filled, fillcolor={color}];')

        # 分析依赖
        if registration.factory:
            dependencies = _extract_dependencies(registration.factory)
            for dep in dependencies:
                dep_name = _format_key(dep)
                lines.append(f'  "{key_name}" -> "{dep_name}";')

    lines.append("}")
    return "\n".join(lines)


def _generate_mermaid(container: Container) -> str:
    """生成 Mermaid 格式."""
    from .types import Lifetime

    lines = ["graph LR", ""]

    registrations = container._registrations

    for key, registration in registrations.items():
        key_name = _format_key(key)

        # 节点样式
        style = {
            Lifetime.SINGLETON: ":::singleton",
            Lifetime.TRANSIENT: ":::transient",
            Lifetime.SCOPED: ":::scoped",
        }.get(registration.lifetime, "")

        lines.append(f"  {key_name}{style}")

        # 分析依赖
        if registration.factory:
            dependencies = _extract_dependencies(registration.factory)
            for dep in dependencies:
                dep_name = _format_key(dep)
                lines.append(f"  {key_name} --> {dep_name}")

    # 添加样式定义
    lines.extend(
        [
            "",
            "  classDef singleton fill:#add8e6",
            "  classDef transient fill:#90ee90",
            "  classDef scoped fill:#ffffe0",
        ]
    )

    return "\n".join(lines)


def print_dependency_graph(container: Container, key: Any = None, indent: int = 0) -> None:
    """打印依赖关系树.

    Args:
        container: 容器实例
        key: 服务键 (None 表示打印所有服务)
        indent: 缩进级别 (内部使用)

    Example:
        >>> print_dependency_graph(container)
        UserService (Singleton)
          ├─ UserRepository (Scoped)
          │  └─ DatabaseContext (Singleton)
          └─ Logger (Singleton)

        >>> # 打印特定服务的依赖树
        >>> print_dependency_graph(container, UserService)
    """
    if key is None:
        # 打印所有顶层服务
        for service_key in container._registrations:
            print_dependency_graph(container, service_key, 0)
            print()
        return

    registration = container._registrations.get(key)
    if not registration:
        print(f"{'  ' * indent}❌ {_format_key(key)} (Not registered)")
        return

    # 使用枚举的 name 属性而不是类名
    lifetime = registration.lifetime.name
    key_name = _format_key(key)

    print(f"{'  ' * indent}{key_name} ({lifetime})")

    if registration.factory:
        dependencies = _extract_dependencies(registration.factory)
        for i, dep in enumerate(dependencies):
            is_last = i == len(dependencies) - 1
            prefix = "└─" if is_last else "├─"
            print(f"{'  ' * indent}{prefix} ", end="")
            print_dependency_graph(container, dep, indent + 1)


def debug_resolution(container: Container, key: Any) -> None:
    """调试服务解析过程.

    打印详细的解析步骤和依赖信息, 帮助诊断问题。

    Args:
        container: 容器实例
        key: 要调试的服务键

    Example:
        >>> debug_resolution(container, UserService)
        🔍 Resolving: UserService
        ✅ Registration found: UserService (Singleton)
        📦 Dependencies:
          - UserRepository (registered: ✅)
          - Logger (registered: ✅)
        🎯 Resolution order:
          1. Logger
          2. UserRepository
          3. UserService
        ✅ Resolution successful
    """
    print(f"🔍 Resolving: {_format_key(key)}")

    registration = container._registrations.get(key)
    if not registration:
        print(f"❌ Service not registered: {_format_key(key)}")
        return

    lifetime = registration.lifetime.name
    print(f"✅ Registration found: {_format_key(key)} ({lifetime})")

    if registration.factory:
        dependencies = _extract_dependencies(registration.factory)
        if dependencies:
            print("📦 Dependencies:")
            for dep in dependencies:
                is_registered = dep in container._registrations
                status = "✅" if is_registered else "❌"
                print(f"  {status} {_format_key(dep)}")

            print("\n🎯 Resolution order:")
            order = _resolve_order(container, key)
            for i, service in enumerate(order, 1):
                print(f"  {i}. {_format_key(service)}")
        else:
            print("📦 No dependencies")
    else:
        print("📦 No factory (instance registration)")

    # 尝试实际解析
    try:
        instance = container.resolve(key)
        print(f"\n✅ Resolution successful: {type(instance).__name__}")
    except Exception as e:
        print(f"\n❌ Resolution failed: {e}")


def diagnose_container(container: Container) -> ContainerDiagnostic:
    """诊断容器健康状态.

    检查循环依赖、无法解析的服务等问题。

    Args:
        container: 容器实例

    Returns:
        诊断报告

    Example:
        >>> report = diagnose_container(container)
        >>> print(f"Health Score: {report.health_score}/100")
        >>> if report.circular_dependencies:
        ...     print("Circular dependencies found!")
        >>> if report.warnings:
        ...     for warning in report.warnings:
        ...         print(f"⚠️  {warning}")
    """
    from .types import Lifetime

    registrations = container._registrations
    total = len(registrations)

    # 统计生命周期
    singleton_count = 0
    transient_count = 0
    scoped_count = 0

    for registration in registrations.values():
        # lifetime 是 Lifetime 枚举
        if registration.lifetime == Lifetime.SINGLETON:
            singleton_count += 1
        elif registration.lifetime == Lifetime.TRANSIENT:
            transient_count += 1
        elif registration.lifetime == Lifetime.SCOPED:
            scoped_count += 1

    # 检查循环依赖
    circular = _detect_circular_dependencies(container)

    # 检查无法解析的服务
    unresolvable = []
    warnings = []

    for key in registrations:
        try:
            container.resolve(key)
        except Exception as e:
            unresolvable.append(key)
            warnings.append(f"{_format_key(key)}: {e}")

    # 计算健康评分
    health_score = 100.0
    if circular:
        health_score -= len(circular) * 20
    if unresolvable:
        health_score -= len(unresolvable) * 10
    health_score = max(0, health_score)

    return ContainerDiagnostic(
        total_services=total,
        singleton_count=singleton_count,
        transient_count=transient_count,
        scoped_count=scoped_count,
        circular_dependencies=circular,
        unresolvable_services=unresolvable,
        warnings=warnings,
        health_score=health_score,
    )


def _format_key(key: Any) -> str:
    """格式化服务键为字符串."""
    if isinstance(key, type):
        return key.__name__
    return str(key).replace(" ", "_").replace("[", "_").replace("]", "_")


def _extract_dependencies(factory: Any) -> list[Any]:
    """从工厂函数提取依赖."""
    if not callable(factory):
        return []

    try:
        sig = inspect.signature(factory)
        dependencies = []
        for param in sig.parameters.values():
            if param.annotation != inspect.Parameter.empty:
                dependencies.append(param.annotation)
        return dependencies
    except Exception:
        return []


def _resolve_order(container: Container, key: Any, visited: set | None = None) -> list:
    """计算解析顺序."""
    if visited is None:
        visited = set()

    if key in visited:
        return []

    visited.add(key)
    order = []

    registration = container._registrations.get(key)
    if registration and registration.factory:
        dependencies = _extract_dependencies(registration.factory)
        for dep in dependencies:
            order.extend(_resolve_order(container, dep, visited))

    order.append(key)
    return order


def _detect_circular_dependencies(container: Container) -> list[tuple[Any, Any]]:
    """检测循环依赖."""
    circular = []

    def visit(key: Any, path: list[Any]) -> None:
        if key in path:
            # 找到循环
            cycle_start = path.index(key)
            circular.append((path[cycle_start], key))
            return

        registration = container._registrations.get(key)
        if not registration or not registration.factory:
            return

        dependencies = _extract_dependencies(registration.factory)
        for dep in dependencies:
            visit(dep, [*path, key])

    for key in container._registrations:
        visit(key, [])

    return circular
