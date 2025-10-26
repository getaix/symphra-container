"""性能优化和监控模块.

提供性能相关的工具和优化:
- 依赖解析缓存优化
- 服务键索引
- 性能计数器和监控
"""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter
from typing import Any


class PerformanceMetrics:
    """性能指标收集器.

    用于收集和报告容器的性能指标.

    Attributes:
        resolution_count: 解析次数
        cache_hits: 缓存命中次数
        cache_misses: 缓存未命中次数
        resolution_times: 解析耗时列表
    """

    def __init__(self) -> None:
        """初始化性能指标."""
        self.resolution_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.resolution_times: list[float] = []
        self.resolution_by_key: dict[Any, int] = defaultdict(int)

    def record_resolution(
        self,
        key: Any,
        elapsed_time: float,
        cache_hit: bool = False,
    ) -> None:
        """记录一次解析.

        Args:
            key: 服务键
            elapsed_time: 解析耗时(秒)
            cache_hit: 是否缓存命中
        """
        self.resolution_count += 1
        self.resolution_times.append(elapsed_time)
        self.resolution_by_key[key] += 1

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def reset(self) -> None:
        """重置所有指标."""
        self.resolution_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.resolution_times.clear()
        self.resolution_by_key.clear()

    @property
    def average_resolution_time(self) -> float:
        """获取平均解析耗时(秒)."""
        if not self.resolution_times:
            return 0.0
        return sum(self.resolution_times) / len(self.resolution_times)

    @property
    def total_resolution_time(self) -> float:
        """获取总解析耗时(秒)."""
        return sum(self.resolution_times)

    @property
    def cache_hit_rate(self) -> float:
        """获取缓存命中率."""
        if self.resolution_count == 0:
            return 0.0
        return self.cache_hits / self.resolution_count

    def get_stats(self) -> dict[str, Any]:
        """获取性能统计信息.

        Returns:
            包含各种性能指标的字典
        """
        return {
            "total_resolutions": self.resolution_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{self.cache_hit_rate * 100:.2f}%",
            "average_resolution_time_ms": f"{self.average_resolution_time * 1000:.3f}",
            "total_resolution_time_ms": f"{self.total_resolution_time * 1000:.3f}",
            "resolutions_by_key": dict(self.resolution_by_key),
        }

    def __repr__(self) -> str:
        """返回字符串表示."""
        return (
            f"PerformanceMetrics("
            f"resolutions={self.resolution_count}, "
            f"cache_hit_rate={self.cache_hit_rate * 100:.1f}%, "
            f"avg_time={self.average_resolution_time * 1000:.3f}ms"
            ")"
        )


class ServiceKeyIndex:
    """服务键索引.

    用于快速查找注册的服务.

    Attributes:
        _index: 键到注册信息的映射
    """

    def __init__(self) -> None:
        """初始化索引."""
        self._index: dict[Any, Any] = {}

    def add(self, key: Any, registration: Any) -> None:
        """添加键到索引.

        Args:
            key: 服务键
            registration: 注册信息
        """
        self._index[key] = registration

    def get(self, key: Any) -> Any | None:
        """获取服务的注册信息.

        Args:
            key: 服务键

        Returns:
            注册信息或 None
        """
        return self._index.get(key)

    def remove(self, key: Any) -> None:
        """移除键.

        Args:
            key: 服务键
        """
        self._index.pop(key, None)

    def contains(self, key: Any) -> bool:
        """检查键是否存在.

        Args:
            key: 服务键

        Returns:
            是否存在
        """
        return key in self._index

    def clear(self) -> None:
        """清空索引."""
        self._index.clear()

    def keys(self) -> list[Any]:
        """获取所有键."""
        return list(self._index.keys())

    def __len__(self) -> int:
        """获取索引中的键数."""
        return len(self._index)


class ResolutionTimer:
    """解析计时器.

    用于测量解析操作的耗时.

    Examples:
        >>> timer = ResolutionTimer()
        >>> with timer:
        ...     # 执行解析操作
        ...     pass
        >>> print(f"耗时: {timer.elapsed_time * 1000:.3f}ms")
    """

    def __init__(self) -> None:
        """初始化计时器."""
        self.start_time: float | None = None
        self.end_time: float | None = None

    def __enter__(self) -> ResolutionTimer:
        """进入上下文,开始计时."""
        self.start_time = perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """离开上下文,停止计时."""
        self.end_time = perf_counter()

    @property
    def elapsed_time(self) -> float:
        """获取经过的时间(秒)."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    def __repr__(self) -> str:
        """返回字符串表示."""
        return f"ResolutionTimer({self.elapsed_time * 1000:.3f}ms)"
