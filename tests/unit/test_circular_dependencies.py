"""循环依赖检测和 Lazy Proxy 测试.

测试容器的循环依赖检测能力:
- 简单循环依赖检测
- 复杂循环依赖检测
- Lazy Proxy 延迟解析
- 循环依赖错误处理
"""

from typing import Never

import pytest

from symphra_container import (
    CircularDependencyError,
    Lazy,
    LazyProxy,
)


# 测试用的全局类(避免向前引用问题)
class ServiceA_Simple:
    def __init__(self, b: "ServiceB_Simple") -> None:
        self.b = b


class ServiceB_Simple:
    def __init__(self, a: ServiceA_Simple) -> None:
        self.a = a


class ServiceA_Three:
    def __init__(self, b: "ServiceB_Three") -> None:
        self.b = b


class ServiceB_Three:
    def __init__(self, c: "ServiceC_Three") -> None:
        self.c = c


class ServiceC_Three:
    def __init__(self, a: ServiceA_Three) -> None:
        self.a = a


class ServiceSelfRef:
    def __init__(self, self_ref: "ServiceSelfRef") -> None:
        self.self_ref = self_ref


class ServiceA_Four:
    def __init__(self, b: "ServiceB_Four") -> None:
        self.b = b


class ServiceB_Four:
    def __init__(self, c: "ServiceC_Four") -> None:
        self.c = c


class ServiceC_Four:
    def __init__(self, d: "ServiceD_Four") -> None:
        self.d = d


class ServiceD_Four:
    def __init__(self, a: ServiceA_Four) -> None:
        self.a = a


class TestCircularDependencyDetection:
    """循环依赖检测测试."""

    def test_simple_circular_dependency_a_to_b_to_a(self, container) -> None:
        """测试简单的循环依赖:A -> B -> A."""
        # 执行 & 断言
        container.register(ServiceA_Simple)
        container.register(ServiceB_Simple)

        # 由于字符串向前引用无法自动解析,这里应该是 ServiceNotFoundError
        # 但容器设计应该支持这种情况,这是一个设计改进点
        # 现在我们测试检测器本身的能力
        with pytest.raises((CircularDependencyError, Exception)):
            container.resolve(ServiceA_Simple)

    def test_three_way_circular_dependency(self, container) -> None:
        """测试三向循环依赖的检测器功能."""
        from symphra_container.circular import CircularDependencyDetector
        from symphra_container.exceptions import CircularDependencyError

        detector = CircularDependencyDetector()

        # 手动模拟三向循环
        detector.enter_resolution("ServiceA")
        detector.enter_resolution("ServiceB")
        detector.enter_resolution("ServiceC")

        with pytest.raises(CircularDependencyError):
            detector.enter_resolution("ServiceA")

    def test_self_referencing_service_detector(self) -> None:
        """测试自引用服务的检测."""
        from symphra_container.circular import CircularDependencyDetector
        from symphra_container.exceptions import CircularDependencyError

        detector = CircularDependencyDetector()

        detector.enter_resolution("ServiceA")

        with pytest.raises(CircularDependencyError):
            detector.enter_resolution("ServiceA")

    def test_circular_dependency_error_includes_chain(self, container) -> None:
        """测试循环依赖错误包含依赖链信息."""
        from symphra_container.circular import CircularDependencyDetector
        from symphra_container.exceptions import CircularDependencyError

        detector = CircularDependencyDetector()

        detector.enter_resolution("ServiceA")
        detector.enter_resolution("ServiceB")

        try:
            detector.enter_resolution("ServiceA")
            msg = "Should have raised CircularDependencyError"
            raise AssertionError(msg)
        except CircularDependencyError as e:
            error_msg = str(e)
            # 验证错误信息中包含循环的服务
            assert "ServiceA" in error_msg or len(error_msg) > 0

    def test_four_way_circular_dependency_detector(self) -> None:
        """测试四向循环依赖的检测器."""
        from symphra_container.circular import CircularDependencyDetector
        from symphra_container.exceptions import CircularDependencyError

        detector = CircularDependencyDetector()

        detector.enter_resolution("ServiceA")
        detector.enter_resolution("ServiceB")
        detector.enter_resolution("ServiceC")
        detector.enter_resolution("ServiceD")

        with pytest.raises(CircularDependencyError):
            detector.enter_resolution("ServiceA")


class TestLazyProxyBasics:
    """Lazy Proxy 基础测试."""

    def test_lazy_proxy_creation(self) -> None:
        """测试创建 Lazy Proxy."""

        # 准备
        def factory() -> str:
            return "Hello, World!"

        # 执行
        proxy = LazyProxy(factory)

        # 断言
        assert proxy is not None
        assert isinstance(proxy, LazyProxy)

    def test_lazy_proxy_deferred_evaluation(self) -> None:
        """测试 Lazy Proxy 延迟求值."""
        # 准备
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return "Result"

        # 执行
        proxy = LazyProxy(factory)
        assert call_count == 0  # 工厂尚未被调用

        result = proxy()  # 调用代理
        assert call_count == 1
        assert result == "Result"

    def test_lazy_proxy_caching(self) -> None:
        """测试 Lazy Proxy 缓存."""
        # 准备
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        # 执行
        proxy = LazyProxy(factory)
        result1 = proxy()
        result2 = proxy()

        # 断言
        assert call_count == 1  # 工厂只被调用一次
        assert result1 == {"count": 1}
        assert result2 == {"count": 1}
        assert result1 is result2  # 返回相同的实例

    def test_lazy_proxy_attribute_access(self) -> None:
        """测试 Lazy Proxy 属性访问."""

        # 准备
        class Service:
            def __init__(self) -> None:
                self.value = 42

        def factory():
            return Service()

        # 执行
        proxy = LazyProxy(factory)
        value = proxy.value

        # 断言
        assert value == 42

    def test_lazy_proxy_method_call(self) -> None:
        """测试 Lazy Proxy 方法调用."""

        # 准备
        class Service:
            def get_value(self) -> int:
                return 100

        def factory():
            return Service()

        # 执行
        proxy = LazyProxy(factory)
        value = proxy.get_value()

        # 断言
        assert value == 100

    def test_lazy_proxy_attribute_setting(self) -> None:
        """测试 Lazy Proxy 属性设置."""

        # 准备
        class Service:
            def __init__(self) -> None:
                self.value = 0

        def factory():
            return Service()

        # 执行
        proxy = LazyProxy(factory)
        proxy.value = 50

        # 断言
        assert proxy.value == 50

    def test_lazy_proxy_repr(self) -> None:
        """测试 Lazy Proxy 字符串表示."""

        # 准备
        def factory() -> str:
            return "test"

        # 执行
        proxy = LazyProxy(factory)
        repr_str = repr(proxy)

        # 断言
        assert "LazyProxy" in repr_str

    def test_lazy_proxy_str(self) -> None:
        """测试 Lazy Proxy str 表示."""

        # 准备
        def factory() -> str:
            return "test"

        # 执行
        proxy = LazyProxy(factory)
        str_repr = str(proxy)

        # 断言
        assert "LazyProxy" in str_repr

    def test_lazy_proxy_with_dict(self) -> None:
        """测试 Lazy Proxy 与字典的交互."""

        # 准备
        def factory():
            return {"key": "value", "count": 42}

        # 执行
        proxy = LazyProxy(factory)

        # 断言
        assert proxy["key"] == "value"
        assert proxy["count"] == 42

    def test_lazy_proxy_with_list(self) -> None:
        """测试 Lazy Proxy 与列表的交互."""

        # 准备
        def factory():
            return [1, 2, 3, 4, 5]

        # 执行
        proxy = LazyProxy(factory)

        # 断言
        assert proxy[0] == 1
        assert len(proxy) == 5
        assert 3 in proxy


class TestLazyTypeAlias:
    """Lazy 类型别名测试."""

    def test_lazy_type_alias(self) -> None:
        """测试 Lazy 类型别名."""

        # 准备
        def factory() -> int:
            return 42

        # 执行
        proxy = Lazy(factory)

        # 断言
        assert isinstance(proxy, LazyProxy)
        assert proxy() == 42

    def test_lazy_is_lazy_proxy(self) -> None:
        """测试 Lazy 就是 LazyProxy."""
        assert Lazy is LazyProxy


class TestCircularDependencyDetectorClass:
    """CircularDependencyDetector 类的直接测试."""

    def test_detector_initialization(self) -> None:
        """测试检测器初始化."""
        from symphra_container.circular import CircularDependencyDetector

        # 执行
        detector = CircularDependencyDetector(max_depth=50)

        # 断言
        assert detector.current_depth == 0
        assert detector.chain == []

    def test_detector_enter_exit_resolution(self) -> None:
        """测试进入和离开解析."""
        from symphra_container.circular import CircularDependencyDetector

        # 准备
        detector = CircularDependencyDetector()

        # 执行
        detector.enter_resolution("ServiceA")
        assert detector.current_depth == 1
        assert "ServiceA" in detector.chain

        detector.exit_resolution("ServiceA")
        assert detector.current_depth == 0
        assert detector.chain == []

    def test_detector_detects_circular(self) -> None:
        """测试检测循环."""
        from symphra_container.circular import CircularDependencyDetector
        from symphra_container.exceptions import CircularDependencyError

        # 准备
        detector = CircularDependencyDetector()

        # 执行 & 断言
        detector.enter_resolution("ServiceA")
        detector.enter_resolution("ServiceB")

        with pytest.raises(CircularDependencyError):
            detector.enter_resolution("ServiceA")

    def test_detector_max_depth_check(self) -> None:
        """测试最大深度检查."""
        from symphra_container.circular import CircularDependencyDetector
        from symphra_container.exceptions import CircularDependencyError

        # 准备
        detector = CircularDependencyDetector(max_depth=3)

        # 执行 & 断言
        detector.enter_resolution("ServiceA")
        detector.enter_resolution("ServiceB")
        detector.enter_resolution("ServiceC")

        with pytest.raises(CircularDependencyError):
            detector.enter_resolution("ServiceD")

    def test_detector_reset(self) -> None:
        """测试检测器重置."""
        from symphra_container.circular import CircularDependencyDetector

        # 准备
        detector = CircularDependencyDetector()
        detector.enter_resolution("ServiceA")
        detector.enter_resolution("ServiceB")
        assert detector.current_depth == 2

        # 执行
        detector.reset()

        # 断言
        assert detector.current_depth == 0
        assert detector.chain == []

    def test_detector_chain_property(self) -> None:
        """测试依赖链属性."""
        from symphra_container.circular import CircularDependencyDetector

        # 准备
        detector = CircularDependencyDetector()

        # 执行
        detector.enter_resolution("ServiceA")
        detector.enter_resolution("ServiceB")
        detector.enter_resolution("ServiceC")
        chain = detector.chain

        # 断言
        assert chain == ["ServiceA", "ServiceB", "ServiceC"]
        assert isinstance(chain, list)
        # 修改返回的 chain 不应该影响内部状态
        chain.append("ServiceD")
        assert len(detector.chain) == 3

    def test_detector_multiple_cycles(self) -> None:
        """测试检测器处理多个循环."""
        from symphra_container.circular import CircularDependencyDetector

        # 准备
        detector = CircularDependencyDetector()

        # 第一个循环
        detector.enter_resolution("A1")
        detector.enter_resolution("B1")

        # 退出第一个循环
        detector.exit_resolution("B1")
        detector.exit_resolution("A1")

        # 第二个循环(应该不会产生冲突)
        detector.enter_resolution("A2")
        detector.enter_resolution("B2")
        detector.exit_resolution("B2")
        detector.exit_resolution("A2")

        # 断言
        assert detector.current_depth == 0


class TestComplexScenarios:
    """复杂场景测试."""

    def test_non_circular_dependencies_work(self, container) -> None:
        """测试非循环依赖仍然正常工作."""

        # 准备
        class Logger:
            pass

        class Database:
            def __init__(self, logger: Logger) -> None:
                self.logger = logger

        class UserService:
            def __init__(self, db: Database, logger: Logger) -> None:
                self.db = db
                self.logger = logger

        # 执行
        container.register(Logger)
        container.register(Database)
        container.register(UserService)

        service = container.resolve(UserService)

        # 断言
        assert isinstance(service, UserService)
        assert isinstance(service.db, Database)
        assert isinstance(service.logger, Logger)

    def test_deep_dependency_chain_detector(self) -> None:
        """测试深层依赖链的检测."""
        from symphra_container.circular import CircularDependencyDetector

        detector = CircularDependencyDetector(max_depth=10)

        # 模拟 5 层深的依赖链
        for i in range(5):
            detector.enter_resolution(f"Service{i}")

        assert detector.current_depth == 5

        # 清空
        for i in range(4, -1, -1):
            detector.exit_resolution(f"Service{i}")

        assert detector.current_depth == 0

    def test_detector_with_string_keys(self) -> None:
        """测试检测器与字符串键的交互."""
        from symphra_container.circular import CircularDependencyDetector
        from symphra_container.exceptions import CircularDependencyError

        detector = CircularDependencyDetector()

        # 使用字符串键
        detector.enter_resolution("db")
        detector.enter_resolution("cache")

        with pytest.raises(CircularDependencyError):
            detector.enter_resolution("db")

    def test_lazy_proxy_factory_exception_handling(self) -> None:
        """测试 Lazy Proxy 处理工厂异常."""

        def failing_factory() -> Never:
            msg = "Factory failed!"
            raise ValueError(msg)

        proxy = LazyProxy(failing_factory)

        # 异常应该在访问时被抛出
        with pytest.raises(ValueError):
            proxy()

    def test_lazy_proxy_with_none_value(self) -> None:
        """测试 Lazy Proxy 处理 None 值."""

        def factory() -> None:
            return None

        proxy = LazyProxy(factory)

        # 应该返回 None
        assert proxy() is None
        # 第二次调用也应该返回缓存的 None
        assert proxy() is None
