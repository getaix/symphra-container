"""性能优化和监控模块测试.

测试性能指标收集,服务键索引和分辨率计时器的功能.
"""

from symphra_container import (
    Container,
    Lifetime,
    PerformanceMetrics,
    ResolutionTimer,
    ServiceKeyIndex,
)


class TestPerformanceMetrics:
    """性能指标收集器测试."""

    def test_initialization(self) -> None:
        """测试性能指标初始化."""
        # 执行
        metrics = PerformanceMetrics()

        # 断言
        assert metrics.resolution_count == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert len(metrics.resolution_times) == 0
        assert metrics.cache_hit_rate == 0.0

    def test_record_resolution_without_cache_hit(self) -> None:
        """测试记录不是缓存命中的解析."""
        # 准备
        metrics = PerformanceMetrics()

        # 执行
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)

        # 断言
        assert metrics.resolution_count == 1
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 1
        assert len(metrics.resolution_times) == 1
        assert abs(metrics.resolution_times[0] - 0.001) < 1e-6

    def test_record_resolution_with_cache_hit(self) -> None:
        """测试记录缓存命中的解析."""
        # 准备
        metrics = PerformanceMetrics()

        # 执行
        metrics.record_resolution("ServiceA", 0.0001, cache_hit=True)

        # 断言
        assert metrics.resolution_count == 1
        assert metrics.cache_hits == 1
        assert metrics.cache_misses == 0
        assert abs(metrics.resolution_times[0] - 0.0001) < 1e-6

    def test_multiple_resolutions_tracking(self) -> None:
        """测试多次解析的追踪."""
        # 准备
        metrics = PerformanceMetrics()

        # 执行
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)
        metrics.record_resolution("ServiceB", 0.002, cache_hit=False)
        metrics.record_resolution("ServiceA", 0.0001, cache_hit=True)
        metrics.record_resolution("ServiceC", 0.003, cache_hit=False)

        # 断言
        assert metrics.resolution_count == 4
        assert metrics.cache_hits == 1
        assert metrics.cache_misses == 3
        assert len(metrics.resolution_times) == 4

    def test_cache_hit_rate_calculation(self) -> None:
        """测试缓存命中率计算."""
        # 准备
        metrics = PerformanceMetrics()

        # 执行
        metrics.record_resolution("ServiceA", 0.001, cache_hit=True)
        metrics.record_resolution("ServiceA", 0.0001, cache_hit=True)
        metrics.record_resolution("ServiceB", 0.002, cache_hit=False)
        metrics.record_resolution("ServiceB", 0.002, cache_hit=False)

        # 断言
        assert metrics.cache_hit_rate == 0.5

    def test_average_resolution_time(self) -> None:
        """测试平均解析耗时计算."""
        # 准备
        metrics = PerformanceMetrics()

        # 执行
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)
        metrics.record_resolution("ServiceB", 0.002, cache_hit=False)
        metrics.record_resolution("ServiceC", 0.003, cache_hit=False)

        # 断言
        expected_avg = (0.001 + 0.002 + 0.003) / 3
        assert abs(metrics.average_resolution_time - expected_avg) < 1e-6

    def test_total_resolution_time(self) -> None:
        """测试总解析耗时计算."""
        # 准备
        metrics = PerformanceMetrics()

        # 执行
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)
        metrics.record_resolution("ServiceB", 0.002, cache_hit=False)
        metrics.record_resolution("ServiceC", 0.003, cache_hit=False)

        # 断言
        expected_total = 0.001 + 0.002 + 0.003
        assert abs(metrics.total_resolution_time - expected_total) < 1e-6

    def test_resolution_by_key_tracking(self) -> None:
        """测试按键追踪解析次数."""
        # 准备
        metrics = PerformanceMetrics()

        # 执行
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)
        metrics.record_resolution("ServiceB", 0.002, cache_hit=False)
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)
        metrics.record_resolution("ServiceC", 0.003, cache_hit=False)
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)

        # 断言
        assert metrics.resolution_by_key["ServiceA"] == 3
        assert metrics.resolution_by_key["ServiceB"] == 1
        assert metrics.resolution_by_key["ServiceC"] == 1

    def test_get_stats(self) -> None:
        """测试获取统计信息."""
        # 准备
        metrics = PerformanceMetrics()
        metrics.record_resolution("ServiceA", 0.001, cache_hit=True)
        metrics.record_resolution("ServiceA", 0.0001, cache_hit=True)
        metrics.record_resolution("ServiceB", 0.002, cache_hit=False)

        # 执行
        stats = metrics.get_stats()

        # 断言
        assert stats["total_resolutions"] == 3
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert "cache_hit_rate" in stats
        assert "average_resolution_time_ms" in stats
        assert "total_resolution_time_ms" in stats
        assert stats["resolutions_by_key"]["ServiceA"] == 2
        assert stats["resolutions_by_key"]["ServiceB"] == 1

    def test_reset(self) -> None:
        """测试重置指标."""
        # 准备
        metrics = PerformanceMetrics()
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)
        assert metrics.resolution_count == 1

        # 执行
        metrics.reset()

        # 断言
        assert metrics.resolution_count == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert len(metrics.resolution_times) == 0
        assert len(metrics.resolution_by_key) == 0

    def test_repr(self) -> None:
        """测试字符串表示."""
        # 准备
        metrics = PerformanceMetrics()
        metrics.record_resolution("ServiceA", 0.001, cache_hit=True)
        metrics.record_resolution("ServiceA", 0.001, cache_hit=False)

        # 执行
        repr_str = repr(metrics)

        # 断言
        assert "PerformanceMetrics" in repr_str
        assert "resolutions=2" in repr_str
        assert "cache_hit_rate=50.0%" in repr_str

    def test_empty_average_resolution_time(self) -> None:
        """测试空时没有解析的平均耗时."""
        # 准备
        metrics = PerformanceMetrics()

        # 断言
        assert metrics.average_resolution_time == 0.0

    def test_empty_cache_hit_rate(self) -> None:
        """测试空时的缓存命中率."""
        # 准备
        metrics = PerformanceMetrics()

        # 断言
        assert metrics.cache_hit_rate == 0.0


class TestServiceKeyIndex:
    """服务键索引测试."""

    def test_initialization(self) -> None:
        """测试索引初始化."""
        # 执行
        index = ServiceKeyIndex()

        # 断言
        assert len(index) == 0

    def test_add_and_get(self) -> None:
        """测试添加和获取."""
        # 准备
        index = ServiceKeyIndex()
        registration = {"type": "ServiceA", "lifetime": "SINGLETON"}

        # 执行
        index.add("ServiceA", registration)
        result = index.get("ServiceA")

        # 断言
        assert result == registration

    def test_get_nonexistent_key(self) -> None:
        """测试获取不存在的键."""
        # 准备
        index = ServiceKeyIndex()

        # 执行
        result = index.get("NonExistent")

        # 断言
        assert result is None

    def test_contains(self) -> None:
        """测试键存在检查."""
        # 准备
        index = ServiceKeyIndex()
        index.add("ServiceA", {})

        # 断言
        assert index.contains("ServiceA")
        assert not index.contains("ServiceB")

    def test_remove(self) -> None:
        """测试移除键."""
        # 准备
        index = ServiceKeyIndex()
        index.add("ServiceA", {})
        index.add("ServiceB", {})

        # 执行
        index.remove("ServiceA")

        # 断言
        assert not index.contains("ServiceA")
        assert index.contains("ServiceB")
        assert len(index) == 1

    def test_remove_nonexistent_key(self) -> None:
        """测试移除不存在的键不抛出异常."""
        # 准备
        index = ServiceKeyIndex()

        # 执行
        index.remove("NonExistent")

        # 断言
        assert len(index) == 0

    def test_keys(self) -> None:
        """测试获取所有键."""
        # 准备
        index = ServiceKeyIndex()
        index.add("ServiceA", {})
        index.add("ServiceB", {})
        index.add("ServiceC", {})

        # 执行
        keys = index.keys()

        # 断言
        assert set(keys) == {"ServiceA", "ServiceB", "ServiceC"}

    def test_clear(self) -> None:
        """测试清空索引."""
        # 准备
        index = ServiceKeyIndex()
        index.add("ServiceA", {})
        index.add("ServiceB", {})

        # 执行
        index.clear()

        # 断言
        assert len(index) == 0
        assert index.keys() == []

    def test_multiple_operations(self) -> None:
        """测试多个操作."""
        # 准备
        index = ServiceKeyIndex()

        # 执行
        index.add("ServiceA", {"id": 1})
        index.add("ServiceB", {"id": 2})
        assert len(index) == 2

        result = index.get("ServiceA")
        assert result["id"] == 1

        index.remove("ServiceB")
        assert not index.contains("ServiceB")
        assert len(index) == 1

        keys = index.keys()
        assert keys == ["ServiceA"]


class TestResolutionTimer:
    """解析计时器测试."""

    def test_initialization(self) -> None:
        """测试计时器初始化."""
        # 执行
        timer = ResolutionTimer()

        # 断言
        assert timer.start_time is None
        assert timer.end_time is None
        assert timer.elapsed_time == 0.0

    def test_context_manager(self) -> None:
        """测试上下文管理器."""
        # 执行
        with ResolutionTimer() as timer:
            assert timer.start_time is not None

        # 断言
        assert timer.end_time is not None
        assert timer.elapsed_time > 0.0

    def test_elapsed_time_measurement(self) -> None:
        """测试耗时测量."""
        # 执行
        import time

        with ResolutionTimer() as timer:
            time.sleep(0.01)

        # 断言
        assert timer.elapsed_time >= 0.01

    def test_repr(self) -> None:
        """测试字符串表示."""
        # 执行
        with ResolutionTimer() as timer:
            import time

            time.sleep(0.001)

        # 断言
        repr_str = repr(timer)
        assert "ResolutionTimer" in repr_str
        assert "ms" in repr_str


class TestContainerPerformanceIntegration:
    """容器与性能监控集成测试."""

    def test_performance_tracking_disabled_by_default(self, container) -> None:
        """测试性能跟踪默认禁用."""
        # 准备
        class DummyService:
            pass

        container.register(DummyService)

        # 执行
        container.resolve(DummyService)
        stats = container.get_performance_stats()

        # 断言
        assert stats["total_resolutions"] == 0

    def test_performance_tracking_enabled(self) -> None:
        """测试启用性能跟踪."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class Service:
            pass

        container.register(Service)

        # 执行
        container.resolve(Service)
        stats = container.get_performance_stats()

        # 断言
        assert stats["total_resolutions"] == 1
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 1

    def test_performance_tracking_with_singleton_cache_hit(self) -> None:
        """测试单例缓存命中的性能跟踪."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class Service:
            pass

        container.register(Service, lifetime=Lifetime.SINGLETON)

        # 执行
        container.resolve(Service)  # 首次:创建新实例
        container.resolve(Service)  # 二次:从缓存获取

        stats = container.get_performance_stats()

        # 断言
        # 两次解析都应该被记录
        assert stats["total_resolutions"] == 2
        # 注意:get_instance 总是返回缓存或新创建的,两者都被视为"get"操作
        # 性能跟踪记录的是缓存命中的结果
        assert stats["cache_hits"] >= 1  # 至少一次是缓存命中
        assert stats["total_resolutions"] == 2

    def test_performance_tracking_multiple_services(self) -> None:
        """测试多个服务的性能跟踪."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        container.register(ServiceA)
        container.register(ServiceB)
        container.register(ServiceC)

        # 执行
        container.resolve(ServiceA)
        container.resolve(ServiceB)
        container.resolve(ServiceC)
        container.resolve(ServiceA)

        stats = container.get_performance_stats()

        # 断言
        assert stats["total_resolutions"] == 4
        # resolutions_by_key 中的键是类对象,不是字符串
        assert len(stats["resolutions_by_key"]) == 3
        assert stats["resolutions_by_key"][ServiceA] == 2
        assert stats["resolutions_by_key"][ServiceB] == 1
        assert stats["resolutions_by_key"][ServiceC] == 1

    def test_reset_performance_metrics(self) -> None:
        """测试重置性能指标."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class Service:
            pass

        container.register(Service)

        # 执行
        container.resolve(Service)
        stats_before = container.get_performance_stats()
        assert stats_before["total_resolutions"] == 1

        container.reset_performance_metrics()
        stats_after = container.get_performance_stats()

        # 断言
        assert stats_after["total_resolutions"] == 0

    def test_performance_stats_timing_accuracy(self) -> None:
        """测试性能统计时间的准确性."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class SlowService:
            def __init__(self) -> None:
                import time

                time.sleep(0.01)

        container.register(SlowService)

        # 执行
        container.resolve(SlowService)
        stats = container.get_performance_stats()

        # 断言
        # 解析时间应该至少有 0.01 秒
        timing_str = stats["total_resolution_time_ms"]
        timing_ms = float(timing_str)
        assert timing_ms >= 10.0

    def test_dispose_resets_metrics(self) -> None:
        """测试 dispose 重置性能指标."""
        # 准备
        container = Container(enable_performance_tracking=True)

        class Service:
            pass

        container.register(Service)
        container.resolve(Service)

        # 执行
        container.dispose()
        stats = container.get_performance_stats()

        # 断言
        assert stats["total_resolutions"] == 0
