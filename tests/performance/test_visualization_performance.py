"""可视化和调试工具性能测试."""

import pytest

from symphra_container import Container, Lifetime
from symphra_container.visualization import (
    debug_resolution,
    diagnose_container,
    print_dependency_graph,
    visualize_container,
)


class Logger:
    """日志服务."""


class Cache:
    """缓存服务."""


class Database:
    """数据库服务."""

    def __init__(self, logger: Logger) -> None:
        self.logger = logger


class Repository:
    """仓储服务."""

    def __init__(self, db: Database, cache: Cache) -> None:
        self.db = db
        self.cache = cache


class Service:
    """业务服务."""

    def __init__(self, repo: Repository, logger: Logger, cache: Cache) -> None:
        self.repo = repo
        self.logger = logger
        self.cache = cache


@pytest.fixture
def simple_container() -> Container:
    """创建简单容器 (5个服务)."""
    container = Container()
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Cache, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)
    container.register(Repository, lifetime=Lifetime.SCOPED)
    container.register(Service, lifetime=Lifetime.TRANSIENT)
    return container


@pytest.fixture
def complex_container() -> Container:
    """创建复杂容器 (50个服务)."""
    container = Container()

    # 创建50个服务，模拟真实应用
    for i in range(50):
        service_class = type(f"Service{i}", (), {})
        lifetime = [Lifetime.SINGLETON, Lifetime.TRANSIENT, Lifetime.SCOPED][i % 3]
        container.register(service_class, lifetime=lifetime)

    return container


def test_visualize_dot_performance_simple(benchmark, simple_container) -> None:
    """测试简单容器的 DOT 可视化性能."""

    def generate_dot() -> str:
        return visualize_container(simple_container, format="dot")

    result = benchmark(generate_dot)
    assert "digraph Container" in result
    assert "Logger" in result


def test_visualize_dot_performance_complex(benchmark, complex_container) -> None:
    """测试复杂容器的 DOT 可视化性能."""

    def generate_dot() -> str:
        return visualize_container(complex_container, format="dot")

    result = benchmark(generate_dot)
    assert "digraph Container" in result


def test_visualize_mermaid_performance_simple(benchmark, simple_container) -> None:
    """测试简单容器的 Mermaid 可视化性能."""

    def generate_mermaid() -> str:
        return visualize_container(simple_container, format="mermaid")

    result = benchmark(generate_mermaid)
    assert "graph LR" in result
    assert "Logger" in result


def test_visualize_mermaid_performance_complex(benchmark, complex_container) -> None:
    """测试复杂容器的 Mermaid 可视化性能."""

    def generate_mermaid() -> str:
        return visualize_container(complex_container, format="mermaid")

    result = benchmark(generate_mermaid)
    assert "graph LR" in result


def test_print_dependency_graph_performance(benchmark, simple_container, capsys) -> None:
    """测试打印依赖图性能."""

    def print_graph() -> None:
        print_dependency_graph(simple_container)

    benchmark(print_graph)

    captured = capsys.readouterr()
    assert "Logger" in captured.out


def test_print_specific_service_graph_performance(benchmark, simple_container, capsys) -> None:
    """测试打印特定服务依赖图性能."""

    def print_graph() -> None:
        print_dependency_graph(simple_container, Service)

    benchmark(print_graph)

    captured = capsys.readouterr()
    assert "Service" in captured.out


def test_debug_resolution_performance(benchmark, simple_container, capsys) -> None:
    """测试调试解析性能."""

    def debug_service() -> None:
        with simple_container.create_scope():
            debug_resolution(simple_container, Service)

    benchmark(debug_service)

    captured = capsys.readouterr()
    assert "Resolving" in captured.out


def test_diagnose_container_performance_simple(benchmark, simple_container) -> None:
    """测试简单容器诊断性能."""

    def diagnose() -> None:
        with simple_container.create_scope():
            return diagnose_container(simple_container)

    result = benchmark(diagnose)
    assert result.total_services == 5
    assert result.health_score >= 0


def test_diagnose_container_performance_complex(benchmark, complex_container) -> None:
    """测试复杂容器诊断性能."""

    def diagnose() -> None:
        with complex_container.create_scope():
            return diagnose_container(complex_container)

    result = benchmark(diagnose)
    assert result.total_services == 50
    assert result.health_score >= 0


def test_visualize_with_many_dependencies_performance(benchmark) -> None:
    """测试具有大量依赖关系的容器可视化性能."""
    container = Container()

    # 创建依赖链: Service1 -> Service2 -> Service3 -> ... -> Service20
    classes = []
    for i in range(20):
        if i == 0:
            service_class = type(f"Service{i}", (), {})
        else:
            prev_class = classes[-1]
            service_class = type(
                f"Service{i}",
                (),
                {"__init__": lambda self, dep=prev_class: setattr(self, "dep", dep)},
            )
        classes.append(service_class)
        container.register(service_class, lifetime=Lifetime.TRANSIENT)

    def generate_visualization() -> str:
        return visualize_container(container, format="dot")

    result = benchmark(generate_visualization)
    assert "digraph Container" in result


def test_diagnose_multiple_times_performance(benchmark, simple_container) -> None:
    """测试多次诊断容器性能 (模拟监控场景)."""

    def diagnose_multiple() -> list:
        results = []
        for _ in range(10):
            with simple_container.create_scope():
                report = diagnose_container(simple_container)
                results.append(report)
        return results

    result = benchmark(diagnose_multiple)
    assert len(result) == 10


def test_visualize_and_diagnose_workflow_performance(benchmark, simple_container) -> None:
    """测试完整的可视化和诊断工作流性能."""

    def full_workflow() -> tuple:
        dot = visualize_container(simple_container, format="dot")
        mermaid = visualize_container(simple_container, format="mermaid")
        with simple_container.create_scope():
            report = diagnose_container(simple_container)
        return (dot, mermaid, report)

    result = benchmark(full_workflow)
    assert len(result) == 3
    assert result[2].total_services == 5


def test_format_key_performance(benchmark) -> None:
    """测试服务键格式化性能."""
    from symphra_container.visualization import _format_key

    # 测试不同类型的键
    keys = [
        Logger,
        "string_key",
        Database,
        Repository,
        Service,
        Cache,
    ]

    def format_all_keys() -> list[str]:
        return [_format_key(key) for key in keys]

    result = benchmark(format_all_keys)
    assert len(result) == 6


def test_extract_dependencies_performance(benchmark) -> None:
    """测试依赖提取性能."""
    from symphra_container.visualization import _extract_dependencies

    def extract_deps() -> list:
        # Database.__init__ 依赖 Logger
        return _extract_dependencies(Database.__init__)

    result = benchmark(extract_deps)
    assert Logger in result


def test_large_container_visualization_memory_efficiency(benchmark) -> None:
    """测试大型容器可视化的内存效率."""
    container = Container()

    # 创建100个服务
    for i in range(100):
        service_class = type(f"Service{i}", (), {})
        container.register(service_class, lifetime=Lifetime.SINGLETON)

    def visualize_large() -> str:
        return visualize_container(container, format="dot")

    result = benchmark(visualize_large)
    assert "digraph Container" in result
    # 验证生成的图不会过大
    assert len(result) < 100000  # 小于100KB


def test_diagnose_with_circular_dependencies_performance(benchmark) -> None:
    """测试诊断循环依赖的性能."""
    container = Container()

    # 注册一些正常服务
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Cache, lifetime=Lifetime.SINGLETON)

    # 注意: 实际循环依赖在运行时会被检测，这里只测试诊断工具的性能
    container.register(Database, lifetime=Lifetime.TRANSIENT)
    container.register(Repository, lifetime=Lifetime.TRANSIENT)

    def diagnose_with_potential_circular() -> None:
        with container.create_scope():
            return diagnose_container(container)

    result = benchmark(diagnose_with_potential_circular)
    assert result.total_services == 4


def test_concurrent_visualization_simulation(benchmark, simple_container) -> None:
    """模拟并发场景下的可视化性能."""

    def simulate_concurrent() -> list[str]:
        results = []
        # 模拟10个并发可视化请求
        for _ in range(10):
            dot = visualize_container(simple_container, format="dot")
            mermaid = visualize_container(simple_container, format="mermaid")
            results.extend([dot, mermaid])
        return results

    result = benchmark(simulate_concurrent)
    assert len(result) == 20


def test_diagnose_health_score_calculation_performance(benchmark) -> None:
    """测试健康评分计算性能."""
    containers = []

    # 创建5个不同健康状态的容器
    for i in range(5):
        container = Container()
        # 添加不同数量的服务
        for j in range((i + 1) * 10):
            service_class = type(f"Service{i}_{j}", (), {})
            container.register(service_class, lifetime=Lifetime.SINGLETON)
        containers.append(container)

    def calculate_health_scores() -> list[float]:
        scores = []
        for c in containers:
            with c.create_scope():
                scores.append(diagnose_container(c).health_score)
        return scores

    result = benchmark(calculate_health_scores)
    assert len(result) == 5
    assert all(score >= 0 for score in result)


def test_print_large_dependency_tree_performance(benchmark, capsys) -> None:
    """测试打印大型依赖树性能."""
    container = Container()

    # 创建具有多层依赖的服务树
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

    container.register(Level1, lifetime=Lifetime.SINGLETON)
    container.register(Level2, lifetime=Lifetime.SINGLETON)
    container.register(Level3, lifetime=Lifetime.SINGLETON)
    container.register(Level4, lifetime=Lifetime.SINGLETON)
    container.register(Level5, lifetime=Lifetime.SINGLETON)

    def print_deep_tree() -> None:
        print_dependency_graph(container, Level5)

    benchmark(print_deep_tree)

    captured = capsys.readouterr()
    assert "Level5" in captured.out
    assert "Level1" in captured.out