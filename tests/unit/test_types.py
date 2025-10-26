"""类型系统测试.

测试核心类型定义.
"""

from symphra_container.types import (
    Injected,
    InjectionMarker,
    Lifetime,
)


class TestLifetime:
    """Lifetime 枚举测试."""

    def test_lifetime_values(self) -> None:
        """测试生命周期值."""
        assert Lifetime.SINGLETON.name == "SINGLETON"
        assert Lifetime.TRANSIENT.name == "TRANSIENT"
        assert Lifetime.SCOPED.name == "SCOPED"
        assert Lifetime.FACTORY.name == "FACTORY"

    def test_lifetime_comparison(self) -> None:
        """测试生命周期比较."""
        assert Lifetime.SINGLETON == Lifetime.SINGLETON
        assert Lifetime.SINGLETON != Lifetime.TRANSIENT
        assert Lifetime.TRANSIENT != Lifetime.SCOPED

    def test_lifetime_in_list(self) -> None:
        """测试生命周期在列表中."""
        lifetimes = [Lifetime.SINGLETON, Lifetime.TRANSIENT]
        assert Lifetime.SINGLETON in lifetimes
        assert Lifetime.SCOPED not in lifetimes


class TestInjectionMarker:
    """InjectionMarker 测试."""

    def test_injected_instance(self) -> None:
        """测试 Injected 实例."""
        assert isinstance(Injected, InjectionMarker)

    def test_injected_repr(self) -> None:
        """测试 Injected 字符串表示."""
        assert repr(Injected) == "Injected"

    def test_injected_is_singleton(self) -> None:
        """测试 Injected 是单例."""
        from symphra_container import Injected as ImportedInjected

        assert Injected is ImportedInjected

    def test_injection_marker_creation(self) -> None:
        """测试创建 InjectionMarker."""
        marker = InjectionMarker()
        assert repr(marker) == "Injected"

    def test_default_parameter_with_injected(self) -> None:
        """测试使用 Injected 作为默认参数."""

        def sample_function(service: str = Injected):
            return service

        # 虽然这不会实际注入,但验证语法是正确的
        assert sample_function.__defaults__ is not None
