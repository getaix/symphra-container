# 测试指南

## 概述

Symphra Container 项目遵循以下测试标准：

- **单元测试覆盖率**: >= 90%
- **集成测试覆盖**: 所有框架集成
- **性能测试**: 关键操作的性能基准
- **测试框架**: pytest + pytest-asyncio + pytest-cov

---

## 单元测试

### 测试目录结构

```
tests/
├── unit/                      # 单元测试
│   ├── test_container.py     # 容器基础功能
│   ├── test_lifetimes.py     # 生命周期管理
│   ├── test_injection.py     # 依赖注入
│   ├── test_circular.py      # 循环依赖处理
│   ├── test_interceptors.py  # 拦截器系统
│   ├── test_decorators.py    # 装饰器系统
│   └── test_async.py         # 异步支持
│
├── integration/               # 集成测试
│   ├── test_fastapi.py       # FastAPI 集成
│   ├── test_flask.py         # Flask 集成
│   ├── test_sqlalchemy.py    # SQLAlchemy 集成
│   └── test_pydantic.py      # Pydantic 集成
│
├── performance/               # 性能测试
│   ├── test_resolution_speed.py
│   ├── test_memory_usage.py
│   └── test_startup_time.py
│
└── conftest.py               # 测试配置和共享夹具
```

### 单元测试示例

```python
# tests/unit/test_container.py

import pytest
from symphra_container import Container, Lifetime
from symphra_container.exceptions import ServiceNotFoundError


class TestContainer:
    """容器基础功能测试"""

    def test_register_and_resolve_instance(self):
        """测试基础的服务注册和解析"""
        # 准备
        container = Container()
        test_obj = object()

        # 执行
        container.register_instance("test_service", test_obj)
        resolved = container.resolve("test_service")

        # 断言
        assert resolved is test_obj

    def test_resolve_nonexistent_service_raises_error(self):
        """测试解析不存在的服务会抛出异常"""
        container = Container()

        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.resolve("non_existent")

        assert "non_existent" in str(exc_info.value)

    @pytest.mark.parametrize("lifetime", [
        Lifetime.SINGLETON,
        Lifetime.TRANSIENT,
        Lifetime.SCOPED,
    ])
    def test_different_lifetimes(self, lifetime):
        """测试不同的生命周期行为"""
        container = Container()

        class Service:
            pass

        container.register(Service, lifetime=lifetime)
        service1 = container.resolve(Service)
        service2 = container.resolve(Service)

        if lifetime == Lifetime.SINGLETON:
            assert service1 is service2
        else:
            assert service1 is not service2


class TestInjection:
    """依赖注入测试"""

    def test_constructor_injection(self):
        """测试构造函数注入"""
        container = Container()

        class Database:
            pass

        class UserService:
            def __init__(self, db: Database):
                self.db = db

        container.register(Database)
        container.register(UserService)

        service = container.resolve(UserService)
        assert isinstance(service.db, Database)

    def test_optional_dependency(self):
        """测试可选依赖的处理"""
        from typing import Optional

        container = Container()

        class Service:
            def __init__(self, optional: Optional[str] = None):
                self.optional = optional

        container.register(Service)
        service = container.resolve(Service)
        assert service.optional is None


class TestAsyncSupport:
    """异步支持测试"""

    @pytest.mark.asyncio
    async def test_async_factory(self):
        """测试异步工厂函数"""
        container = Container()

        async def create_service():
            # 模拟异步操作
            return "async_service"

        container.register_async_factory("service", create_service)
        result = await container.resolve_async("service")
        assert result == "async_service"
```

---

## 集成测试

### FastAPI 集成测试

```python
# tests/integration/test_fastapi.py

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from symphra_container import Container, Injected
from symphra_container.integrations.fastapi import DIMiddleware


@pytest.fixture
def app_with_container():
    """创建集成 DI 容器的 FastAPI 应用"""
    app = FastAPI()
    container = Container()

    # 注册服务
    class UserService:
        def get_user(self, user_id: int):
            return {"id": user_id, "name": "Test User"}

    container.register(UserService)
    app.add_middleware(DIMiddleware, container=container)

    return app, container


def test_fastapi_injection(app_with_container):
    """测试 FastAPI 中的依赖注入"""
    app, container = app_with_container

    @app.get("/users/{user_id}")
    def get_user(user_id: int, service: "UserService" = Injected):
        return service.get_user(user_id)

    client = TestClient(app)
    response = client.get("/users/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1


@pytest.mark.asyncio
async def test_fastapi_async_injection():
    """测试 FastAPI 中的异步依赖注入"""
    app = FastAPI()
    container = Container()

    class AsyncService:
        async def process(self, data: str):
            return f"processed: {data}"

    container.register(AsyncService)
    app.add_middleware(DIMiddleware, container=container)

    @app.get("/process")
    async def process(service: "AsyncService" = Injected):
        return await service.process("test")

    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/process")

    assert response.status_code == 200
```

---

## 性能测试

### 性能基准测试

```python
# tests/performance/test_resolution_speed.py

import pytest
import time
from symphra_container import Container, Lifetime


class TestResolutionPerformance:
    """解析性能测试"""

    def test_singleton_resolution_speed(self):
        """测试单例解析的速度（应该 < 100ns）"""
        container = Container()

        class Service:
            pass

        container.register(Service, lifetime=Lifetime.SINGLETON)

        # 预热
        container.resolve(Service)

        # 性能测试
        start = time.perf_counter_ns()
        for _ in range(100000):
            container.resolve(Service)
        duration_ns = time.perf_counter_ns() - start

        avg_ns = duration_ns / 100000
        print(f"平均解析时间: {avg_ns:.2f} ns")

        # 断言：平均解析时间应该 < 1000 ns (1 μs)
        assert avg_ns < 1000

    def test_complex_dependency_resolution(self):
        """测试复杂依赖解析的速度"""
        container = Container()

        class A:
            pass

        class B:
            def __init__(self, a: A):
                self.a = a

        class C:
            def __init__(self, b: B):
                self.b = b

        class D:
            def __init__(self, c: C):
                self.c = c

        container.register(A, lifetime=Lifetime.SINGLETON)
        container.register(B, lifetime=Lifetime.TRANSIENT)
        container.register(C, lifetime=Lifetime.TRANSIENT)
        container.register(D, lifetime=Lifetime.TRANSIENT)

        start = time.perf_counter_ns()
        for _ in range(10000):
            container.resolve(D)
        duration_ns = time.perf_counter_ns() - start

        avg_ns = duration_ns / 10000
        print(f"复杂依赖平均解析时间: {avg_ns:.2f} ns")

        # 应该在可接受范围内
        assert avg_ns < 50000  # < 50 μs


class TestMemoryUsage:
    """内存使用测试"""

    def test_memory_efficiency(self):
        """测试内存使用效率"""
        import sys

        container = Container()

        # 注册 1000 个服务
        for i in range(1000):
            class Service:
                pass

            container.register(f"service_{i}", Service)

        # 获取容器的大致内存占用
        size = sys.getsizeof(container)
        print(f"1000 个服务的容器大小: {size / 1024:.2f} KB")

        # 应该在合理范围内 (< 10 MB)
        assert size < 10 * 1024 * 1024
```

---

## 运行测试

### 快速测试

```bash
# 运行所有单元测试
uv run pytest tests/unit/ -v

# 运行特定测试文件
uv run pytest tests/unit/test_container.py -v

# 运行特定测试函数
uv run pytest tests/unit/test_container.py::TestContainer::test_register_and_resolve_instance -v
```

### 完整测试和覆盖率

```bash
# 运行所有测试并生成覆盖率报告
uv run pytest tests/ -v --cov=src/symphra_container --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html  # macOS
# 或
xdg-open htmlcov/index.html  # Linux
# 或
start htmlcov/index.html  # Windows
```

### 分类运行测试

```bash
# 只运行单元测试
uv run pytest tests/unit/ -v -m "not integration and not performance"

# 只运行集成测试
uv run pytest tests/integration/ -v -m "integration"

# 只运行性能测试
uv run pytest tests/performance/ -v -m "performance"

# 运行除了慢测试外的所有测试
uv run pytest tests/ -v -m "not slow"
```

---

## 测试覆盖率要求

### 最低要求

- **总体覆盖率**: >= 90%
- **关键模块**: 100%
  - `container.py`
  - `injection/`
  - `lifetimes/`
  - `circular/`

### 查看详细覆盖率

```bash
# 查看哪些行未覆盖
uv run pytest tests/ --cov --cov-report=term-missing

# 生成 HTML 报告（更清晰）
uv run pytest tests/ --cov --cov-report=html
# 打开 htmlcov/index.html 查看具体未覆盖的代码
```

---

## 最佳实践

### 1. 编写清晰的测试

```python
# ✅ 好的测试
def test_container_resolves_singleton_once():
    """容器应该为单例生命周期的服务返回同一实例"""
    container = Container()
    container.register("service", Service, lifetime=Lifetime.SINGLETON)

    instance1 = container.resolve("service")
    instance2 = container.resolve("service")

    assert instance1 is instance2

# ❌ 不好的测试
def test_container():
    container = Container()
    container.register("s", Service)
    assert container.resolve("s") is container.resolve("s")
```

### 2. 使用 fixtures 减少重复代码

```python
@pytest.fixture
def container():
    """每个测试都会得到一个新的容器实例"""
    return Container()

def test_with_fixture(container):
    container.register("service", Service)
    assert container.resolve("service") is not None
```

### 3. 参数化测试

```python
@pytest.mark.parametrize("lifetime", [
    Lifetime.SINGLETON,
    Lifetime.TRANSIENT,
    Lifetime.SCOPED,
])
def test_different_lifetimes(lifetime):
    """同一个测试逻辑，多个参数值"""
    container = Container()
    container.register(Service, lifetime=lifetime)
    # 测试逻辑...
```

### 4. 异步测试

```python
@pytest.mark.asyncio
async def test_async_operation():
    """异步测试需要 pytest.mark.asyncio 标记"""
    container = Container()
    result = await container.resolve_async(AsyncService)
    assert result is not None
```

---

## 持续集成

GitHub Actions 会自动运行所有测试：

```bash
# 在本地模拟 CI
make check  # 运行所有检查
```

详见 `.github/workflows/ci.yml`。
