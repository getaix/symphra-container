"""pytest 配置和共享测试夹具.

定义了所有单元测试使用的公共 fixtures 和配置.

Fixtures:
    container: 一个干净的容器实例
    cleanup: 容器清理器
"""

import pytest

from symphra_container import Container


@pytest.fixture
def container() -> Container:
    """创建一个容器实例.

    每个测试都会获得一个新的容器实例,避免测试间的相互影响.

    Yields:
        一个新的 Container 实例
    """
    container = Container()
    yield container
    # 清理
    container.dispose()


@pytest.fixture
def cleanup():
    """提供容器清理函数.

    用于手动清理容器资源.

    Returns:
        清理函数
    """
    containers = []

    def add_container(c: Container) -> None:
        """添加容器到清理列表."""
        containers.append(c)

    yield add_container

    # 清理所有容器
    for c in containers:
        c.dispose()


# 标记定义
def pytest_configure(config) -> None:
    """配置 pytest 标记."""
    config.addinivalue_line(
        "markers",
        "asyncio: 异步测试标记",
    )
    config.addinivalue_line(
        "markers",
        "integration: 集成测试标记",
    )
    config.addinivalue_line(
        "markers",
        "performance: 性能测试标记",
    )
    config.addinivalue_line(
        "markers",
        "slow: 慢速测试标记",
    )
