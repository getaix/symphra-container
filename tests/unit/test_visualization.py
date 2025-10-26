"""测试可视化和调试工具."""

import pytest

from symphra_container import Container, Lifetime
from symphra_container.visualization import (
    ContainerDiagnostic,
    debug_resolution,
    diagnose_container,
    print_dependency_graph,
    visualize_container,
)


class Logger:
    """日志服务."""



class Database:
    """数据库服务."""

    def __init__(self, logger: Logger) -> None:
        self.logger = logger


class UserRepository:
    """用户仓储."""

    def __init__(self, db: Database) -> None:
        self.db = db


class UserService:
    """用户服务."""

    def __init__(self, repo: UserRepository, logger: Logger) -> None:
        self.repo = repo
        self.logger = logger


def test_visualize_container_dot_format():
    """测试生成 DOT 格式的可视化图."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)
    container.register(UserRepository, lifetime=Lifetime.SCOPED)
    container.register(UserService, lifetime=Lifetime.TRANSIENT)

    dot = visualize_container(container, format="dot")

    # 验证基本结构
    assert "digraph Container" in dot
    assert "Logger" in dot
    assert "Database" in dot
    assert "UserRepository" in dot
    assert "UserService" in dot

    # 验证依赖关系
    assert "->" in dot


def test_visualize_container_mermaid_format():
    """测试生成 Mermaid 格式的可视化图."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)

    mermaid = visualize_container(container, format="mermaid")

    # 验证基本结构
    assert "graph LR" in mermaid
    assert "Logger" in mermaid
    assert "Database" in mermaid

    # 验证样式定义
    assert "classDef singleton" in mermaid
    assert "classDef transient" in mermaid
    assert "classDef scoped" in mermaid


def test_visualize_container_invalid_format():
    """测试无效格式时抛出异常."""
    container = Container()

    with pytest.raises(ValueError, match="Unsupported format"):
        visualize_container(container, format="invalid")


def test_print_dependency_graph_all_services(capsys):
    """测试打印所有服务的依赖图."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)
    container.register(UserRepository, lifetime=Lifetime.SCOPED)

    print_dependency_graph(container)

    captured = capsys.readouterr()
    assert "Logger" in captured.out
    assert "Database" in captured.out
    assert "UserRepository" in captured.out


def test_print_dependency_graph_specific_service(capsys):
    """测试打印特定服务的依赖树."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)

    print_dependency_graph(container, Database)

    captured = capsys.readouterr()
    assert "Database" in captured.out
    assert "Logger" in captured.out  # Database 依赖 Logger


def test_print_dependency_graph_not_registered(capsys):
    """测试打印未注册服务的信息."""
    container = Container()

    print_dependency_graph(container, Logger)

    captured = capsys.readouterr()
    assert "Not registered" in captured.out


def test_debug_resolution_success(capsys):
    """测试调试成功的服务解析."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)

    debug_resolution(container, Database)

    captured = capsys.readouterr()
    assert "Resolving" in captured.out
    assert "Database" in captured.out
    assert "Logger" in captured.out
    assert "Resolution successful" in captured.out


def test_debug_resolution_not_registered(capsys):
    """测试调试未注册的服务."""
    container = Container()

    debug_resolution(container, Logger)

    captured = capsys.readouterr()
    assert "Service not registered" in captured.out


def test_debug_resolution_with_dependencies(capsys):
    """测试调试有依赖的服务."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)
    container.register(UserRepository, lifetime=Lifetime.SCOPED)

    debug_resolution(container, UserRepository)

    captured = capsys.readouterr()
    assert "Dependencies" in captured.out
    assert "Database" in captured.out
    assert "Resolution order" in captured.out


def test_diagnose_container_healthy():
    """测试诊断健康的容器."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)
    container.register(UserRepository, lifetime=Lifetime.SCOPED)
    container.register(UserService, lifetime=Lifetime.TRANSIENT)

    report = diagnose_container(container)

    assert isinstance(report, ContainerDiagnostic)
    assert report.total_services == 4
    assert report.singleton_count == 2
    assert report.scoped_count == 1
    assert report.transient_count == 1
    assert len(report.circular_dependencies) == 0
    assert len(report.unresolvable_services) == 0
    assert report.health_score == 100.0


def test_diagnose_container_with_unresolvable():
    """测试诊断有无法解析服务的容器."""
    container = Container()

    # 注册一个依赖未满足的服务
    container.register(Database, lifetime=Lifetime.SINGLETON)  # 依赖 Logger, 但 Logger 未注册

    report = diagnose_container(container)

    assert len(report.unresolvable_services) > 0
    assert len(report.warnings) > 0
    assert report.health_score < 100.0


def test_diagnose_container_empty():
    """测试诊断空容器."""
    container = Container()

    report = diagnose_container(container)

    assert report.total_services == 0
    assert report.singleton_count == 0
    assert report.transient_count == 0
    assert report.scoped_count == 0
    assert report.health_score == 100.0


def test_container_diagnostic_dataclass():
    """测试 ContainerDiagnostic 数据类."""
    report = ContainerDiagnostic(
        total_services=10,
        singleton_count=5,
        transient_count=3,
        scoped_count=2,
        circular_dependencies=[],
        unresolvable_services=[],
        warnings=[],
        health_score=100.0,
    )

    assert report.total_services == 10
    assert report.singleton_count == 5
    assert report.health_score == 100.0


def test_visualize_with_string_keys():
    """测试可视化带字符串键的服务."""
    container = Container()
    container.register(Logger, key="logger", lifetime=Lifetime.SINGLETON)

    dot = visualize_container(container, format="dot")
    assert "logger" in dot


def test_debug_with_factory_registration(capsys):
    """测试调试工厂注册的服务."""
    container = Container()

    # 使用工厂注册
    container.register_factory(Logger, lambda: Logger(), lifetime=Lifetime.SINGLETON)

    debug_resolution(container, Logger)

    captured = capsys.readouterr()
    assert "Logger" in captured.out


def test_diagnose_container_lifecycle_distribution():
    """测试诊断容器生命周期分布."""
    container = Container()

    # 注册不同生命周期的服务
    for i in range(5):
        container.register(type(f"Service{i}", (), {}), lifetime=Lifetime.SINGLETON)

    for i in range(5, 8):
        container.register(type(f"Service{i}", (), {}), lifetime=Lifetime.TRANSIENT)

    for i in range(8, 10):
        container.register(type(f"Service{i}", (), {}), lifetime=Lifetime.SCOPED)

    report = diagnose_container(container)

    assert report.singleton_count == 5
    assert report.transient_count == 3
    assert report.scoped_count == 2
    assert report.total_services == 10
