"""依赖注入功能测试.

测试容器的依赖注入能力:
- 构造函数注入
- 依赖分析
- 类型提示支持
- 可选依赖
"""

import pytest

from symphra_container import (
    Injected,
    Lifetime,
    ServiceNotFoundError,
)


class TestConstructorInjection:
    """构造函数注入测试."""

    def test_simple_constructor_injection(self, container) -> None:
        """测试简单的构造函数注入."""

        # 准备
        class Database:
            pass

        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行
        container.register(Database)
        container.register(UserService)
        service = container.resolve(UserService)

        # 断言
        assert isinstance(service, UserService)
        assert isinstance(service.db, Database)

    def test_nested_dependency_injection(self, container) -> None:
        """测试嵌套依赖注入."""

        # 准备
        class Database:
            pass

        class Repository:
            def __init__(self, db: Database) -> None:
                self.db = db

        class UserService:
            def __init__(self, repo: Repository) -> None:
                self.repo = repo

        # 执行
        container.register(Database)
        container.register(Repository)
        container.register(UserService)
        service = container.resolve(UserService)

        # 断言
        assert isinstance(service, UserService)
        assert isinstance(service.repo, Repository)
        assert isinstance(service.repo.db, Database)

    def test_string_key_injection(self, container) -> None:
        """测试服务解析支持多种键."""

        # 准备
        class Database:
            pass

        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行 - 注册类型键
        container.register(Database)
        container.register(UserService)

        # 也可以通过类型键解析
        db = container.resolve(Database)

        # 直接解析服务
        service = container.resolve(UserService)

        # 断言
        assert isinstance(service, UserService)
        assert isinstance(service.db, Database)
        assert isinstance(db, Database)

    def test_multiple_dependencies(self, container) -> None:
        """测试多个依赖注入."""

        # 准备
        class Logger:
            pass

        class Database:
            pass

        class Cache:
            pass

        class UserService:
            def __init__(self, logger: Logger, db: Database, cache: Cache) -> None:
                self.logger = logger
                self.db = db
                self.cache = cache

        # 执行
        container.register(Logger)
        container.register(Database)
        container.register(Cache)
        container.register(UserService)
        service = container.resolve(UserService)

        # 断言
        assert isinstance(service, UserService)
        assert isinstance(service.logger, Logger)
        assert isinstance(service.db, Database)
        assert isinstance(service.cache, Cache)


class TestOptionalDependencies:
    """可选依赖测试."""

    def test_optional_dependency_not_registered(self, container) -> None:
        """测试可选依赖未注册时的处理."""

        # 准备
        class Service:
            def __init__(self, optional: str | None = None) -> None:
                self.optional = optional

        # 执行
        container.register(Service)
        service = container.resolve(Service)

        # 断言
        assert isinstance(service, Service)
        assert service.optional is None

    def test_optional_dependency_registered(self, container) -> None:
        """测试可选依赖已注册时的注入."""

        # 准备
        class OptionalService:
            pass

        class Service:
            def __init__(self, opt_service: OptionalService | None = None) -> None:
                self.opt_service = opt_service

        # 执行
        container.register(OptionalService)
        container.register(Service)
        service = container.resolve(Service)

        # 断言
        assert isinstance(service, Service)
        assert isinstance(service.opt_service, OptionalService)

    def test_multiple_optional_dependencies(self, container) -> None:
        """测试多个可选依赖."""

        # 准备
        class ServiceA:
            pass

        class ServiceB:
            pass

        class MainService:
            def __init__(
                self,
                a: ServiceA | None = None,
                b: ServiceB | None = None,
            ) -> None:
                self.a = a
                self.b = b

        # 执行
        container.register(ServiceA)
        # ServiceB 没有注册
        container.register(MainService)
        service = container.resolve(MainService)

        # 断言
        assert isinstance(service, MainService)
        assert isinstance(service.a, ServiceA)
        assert service.b is None


class TestInjectedMarker:
    """Injected 标记测试."""

    def test_injected_marker_in_function(self) -> None:
        """测试 Injected 标记的存在."""
        # 断言
        assert Injected is not None
        assert isinstance(Injected, object)

    def test_default_parameters_with_injected(self, container) -> None:
        """测试使用 Injected 标记的默认参数."""

        # 准备
        class Service:
            pass

        class Consumer:
            def __init__(self, service: Service = Injected) -> None:
                self.service = service

        # 执行
        container.register(Service)
        container.register(Consumer)
        consumer = container.resolve(Consumer)

        # 断言
        assert isinstance(consumer, Consumer)
        assert isinstance(consumer.service, Service)


class TestLifetimeWithDependencies:
    """包含依赖的生命周期测试."""

    def test_singleton_with_singleton_dependency(self, container) -> None:
        """测试单例包含单例依赖的情况."""

        # 准备
        class Database:
            pass

        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行
        container.register(Database, lifetime=Lifetime.SINGLETON)
        container.register(UserService, lifetime=Lifetime.SINGLETON)
        service1 = container.resolve(UserService)
        service2 = container.resolve(UserService)

        # 断言
        assert service1 is service2
        assert service1.db is service2.db

    def test_transient_with_singleton_dependency(self, container) -> None:
        """测试瞬时包含单例依赖的情况."""

        # 准备
        class Database:
            pass

        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行
        container.register(Database, lifetime=Lifetime.SINGLETON)
        container.register(UserService, lifetime=Lifetime.TRANSIENT)
        service1 = container.resolve(UserService)
        service2 = container.resolve(UserService)

        # 断言
        assert service1 is not service2
        assert service1.db is service2.db  # 依赖仍然是同一个


class TestErrorHandlingInInjection:
    """注入错误处理测试."""

    def test_missing_required_dependency(self, container) -> None:
        """测试缺少必需依赖时的错误."""

        # 准备
        class Database:
            pass

        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行 & 断言
        container.register(UserService)

        with pytest.raises(ServiceNotFoundError):
            container.resolve(UserService)

    def test_circular_dependency_simple(self, container) -> None:
        """测试简单的循环依赖检测."""
        # 注意:这个测试需要在运行时检测循环,
        # 由于我们的实现需要完整的循环依赖检测,
        # 这里先记录 - 会在后续优化中实现


class TestDependencyAnalysis:
    """依赖分析测试."""

    def test_analyze_simple_dependencies(self) -> None:
        """测试分析简单依赖."""
        # 准备
        from symphra_container.injector import ConstructorInjector

        class Database:
            pass

        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行
        dependencies = ConstructorInjector.analyze_dependencies(UserService)

        # 断言
        assert len(dependencies) == 1
        assert dependencies[0].parameter_name == "db"
        assert dependencies[0].service_type == Database

    def test_analyze_multiple_dependencies(self) -> None:
        """测试分析多个依赖."""
        # 准备
        from symphra_container.injector import ConstructorInjector

        class Logger:
            pass

        class Database:
            pass

        class UserService:
            def __init__(self, logger: Logger, db: Database) -> None:
                self.logger = logger
                self.db = db

        # 执行
        dependencies = ConstructorInjector.analyze_dependencies(UserService)

        # 断言
        assert len(dependencies) == 2
        param_names = {dep.parameter_name for dep in dependencies}
        assert param_names == {"logger", "db"}

    def test_analyze_optional_dependencies(self) -> None:
        """测试分析可选依赖."""
        # 准备
        from symphra_container.injector import ConstructorInjector

        class Logger:
            pass

        class UserService:
            def __init__(self, logger: Logger | None = None) -> None:
                self.logger = logger

        # 执行
        dependencies = ConstructorInjector.analyze_dependencies(UserService)

        # 断言
        assert len(dependencies) == 1
        assert dependencies[0].is_optional is True
