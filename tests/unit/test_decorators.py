"""装饰器系统测试.

测试服务装饰器的功能:
- @injectable 装饰器
- @singleton, @transient, @scoped 生命周期装饰器
- @factory 工厂装饰器
- 自动注册功能
"""

from symphra_container import Lifetime
from symphra_container.decorators import (
    ServiceMetadata,
    auto_register,
    factory,
    get_service_metadata,
    injectable,
    is_injectable,
    scoped,
    singleton,
    transient,
)


class TestInjectableDecorator:
    """@injectable 装饰器测试."""

    def test_injectable_without_args(self) -> None:
        """测试无参数的 @injectable."""

        # 执行
        @injectable
        class Service:
            pass

        # 断言
        assert is_injectable(Service)
        metadata = get_service_metadata(Service)
        assert metadata is not None
        assert metadata.lifetime == Lifetime.TRANSIENT
        assert metadata.key == Service

    def test_injectable_with_lifetime(self) -> None:
        """测试带生命周期的 @injectable."""

        # 执行
        @injectable(Lifetime.SINGLETON)
        class Service:
            pass

        # 断言
        assert is_injectable(Service)
        metadata = get_service_metadata(Service)
        assert metadata.lifetime == Lifetime.SINGLETON

    def test_injectable_with_key(self) -> None:
        """测试带自定义键的 @injectable."""

        # 执行
        @injectable(key="custom_service")
        class Service:
            pass

        # 断言
        metadata = get_service_metadata(Service)
        assert metadata.key == "custom_service"

    def test_injectable_with_lifetime_and_key(self) -> None:
        """测试带生命周期和键的 @injectable."""

        # 执行
        @injectable(Lifetime.SCOPED, key="db_service")
        class DatabaseService:
            pass

        # 断言
        metadata = get_service_metadata(DatabaseService)
        assert metadata.lifetime == Lifetime.SCOPED
        assert metadata.key == "db_service"

    def test_injectable_metadata_attributes(self) -> None:
        """测试元数据的属性."""

        # 执行
        @injectable(Lifetime.SINGLETON, key="test")
        class Service:
            pass

        metadata = get_service_metadata(Service)

        # 断言
        assert isinstance(metadata, ServiceMetadata)
        assert metadata.service_type == Service
        assert metadata.lifetime == Lifetime.SINGLETON
        assert metadata.key == "test"


class TestLifecycleDecorators:
    """生命周期装饰器测试."""

    def test_singleton_decorator(self) -> None:
        """测试 @singleton 装饰器."""

        # 执行
        @singleton
        class Service:
            pass

        # 断言
        metadata = get_service_metadata(Service)
        assert metadata.lifetime == Lifetime.SINGLETON

    def test_transient_decorator(self) -> None:
        """测试 @transient 装饰器."""

        # 执行
        @transient
        class Service:
            pass

        # 断言
        metadata = get_service_metadata(Service)
        assert metadata.lifetime == Lifetime.TRANSIENT

    def test_scoped_decorator(self) -> None:
        """测试 @scoped 装饰器."""

        # 执行
        @scoped
        class Service:
            pass

        # 断言
        metadata = get_service_metadata(Service)
        assert metadata.lifetime == Lifetime.SCOPED

    def test_all_decorators_are_injectable(self) -> None:
        """测试所有生命周期装饰器都标记为 injectable."""

        # 执行
        @singleton
        class ServiceA:
            pass

        @transient
        class ServiceB:
            pass

        @scoped
        class ServiceC:
            pass

        # 断言
        assert is_injectable(ServiceA)
        assert is_injectable(ServiceB)
        assert is_injectable(ServiceC)


class TestFactoryDecorator:
    """@factory 装饰器测试."""

    def test_factory_without_args(self) -> None:
        """测试无参数的 @factory."""

        # 执行
        @factory()
        def create_service() -> str:
            return "service"

        # 断言
        assert is_injectable(create_service)
        metadata = get_service_metadata(create_service)
        assert metadata.key == "create_service"

    def test_factory_with_lifetime(self) -> None:
        """测试带生命周期的 @factory."""

        # 执行
        @factory(Lifetime.SINGLETON)
        def create_service() -> str:
            return "service"

        # 断言
        metadata = get_service_metadata(create_service)
        assert metadata.lifetime == Lifetime.SINGLETON

    def test_factory_with_key(self) -> None:
        """测试带键的 @factory."""

        # 执行
        @factory(key="my_service")
        def create_service() -> str:
            return "service"

        # 断言
        metadata = get_service_metadata(create_service)
        assert metadata.key == "my_service"

    def test_factory_with_lifetime_and_key(self) -> None:
        """测试带生命周期和键的 @factory."""

        # 执行
        @factory(Lifetime.SINGLETON, key="config_factory")
        def create_config():
            return {"debug": True}

        # 断言
        metadata = get_service_metadata(create_config)
        assert metadata.lifetime == Lifetime.SINGLETON
        assert metadata.key == "config_factory"

    def test_factory_function_still_works(self) -> None:
        """测试被装饰的工厂函数仍可正常调用."""

        # 执行
        @factory()
        def create_service():
            return {"value": 42}

        result = create_service()

        # 断言
        assert result == {"value": 42}


class TestAutoRegister:
    """auto_register 功能测试."""

    def test_auto_register_single_service(self, container) -> None:
        """测试注册单个服务."""

        # 准备
        @injectable
        class Service:
            pass

        # 执行
        auto_register(container, Service)

        # 断言
        assert container.is_registered(Service)
        service = container.resolve(Service)
        assert isinstance(service, Service)

    def test_auto_register_multiple_services(self, container) -> None:
        """测试注册多个服务."""

        # 准备
        @singleton
        class DatabaseService:
            pass

        @transient
        class UserService:
            pass

        @scoped
        class RequestService:
            pass

        # 执行
        auto_register(container, DatabaseService, UserService, RequestService)

        # 断言
        assert container.is_registered(DatabaseService)
        assert container.is_registered(UserService)
        assert container.is_registered(RequestService)

        # 验证生命周期
        db1 = container.resolve(DatabaseService)
        db2 = container.resolve(DatabaseService)
        assert db1 is db2  # Singleton

        user1 = container.resolve(UserService)
        user2 = container.resolve(UserService)
        assert user1 is not user2  # Transient

    def test_auto_register_preserves_lifetime(self, container) -> None:
        """测试自动注册保留生命周期."""

        # 准备
        @singleton
        class Service:
            pass

        # 执行
        auto_register(container, Service)

        # 断言
        service1 = container.resolve(Service)
        service2 = container.resolve(Service)
        assert service1 is service2

    def test_auto_register_with_custom_key(self, container) -> None:
        """测试带自定义键的自动注册."""

        # 准备
        @injectable(key="my_service")
        class Service:
            pass

        # 执行
        auto_register(container, Service)

        # 断言
        service = container.resolve("my_service")
        assert isinstance(service, Service)

    def test_auto_register_undecorated_class(self, container) -> None:
        """测试注册未装饰的类(使用默认 TRANSIENT)."""

        # 准备
        class Service:
            pass

        # 执行
        auto_register(container, Service)

        # 断言
        assert container.is_registered(Service)
        service1 = container.resolve(Service)
        service2 = container.resolve(Service)
        assert service1 is not service2  # Transient by default


class TestDecoratorIntegration:
    """装饰器与容器的集成测试."""

    def test_decorated_service_with_dependencies(self, container) -> None:
        """测试装饰服务与依赖的交互."""

        # 准备
        @singleton
        class Logger:
            pass

        @injectable
        class Service:
            def __init__(self, logger: Logger) -> None:
                self.logger = logger

        # 执行
        auto_register(container, Logger, Service)
        service = container.resolve(Service)

        # 断言
        assert isinstance(service, Service)
        assert isinstance(service.logger, Logger)

    def test_multiple_decorated_services_with_dependencies(self, container) -> None:
        """测试多个装饰服务之间的依赖."""

        # 准备
        @singleton
        class Config:
            pass

        @singleton
        class Database:
            def __init__(self, config: Config) -> None:
                self.config = config

        @transient
        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行
        auto_register(container, Config, Database, UserService)
        user_service = container.resolve(UserService)

        # 断言
        assert isinstance(user_service, UserService)
        assert isinstance(user_service.db, Database)
        assert isinstance(user_service.db.config, Config)

    def test_decorated_service_lifecycle_in_container(self, container) -> None:
        """测试装饰服务的生命周期在容器中被正确应用."""
        # 准备

        @singleton
        class SingletonService:
            pass

        @transient
        class TransientService:
            pass

        # 执行
        auto_register(container, SingletonService, TransientService)

        # 解析多次
        s1 = container.resolve(SingletonService)
        s2 = container.resolve(SingletonService)
        t1 = container.resolve(TransientService)
        t2 = container.resolve(TransientService)

        # 断言
        assert s1 is s2  # 单例
        assert t1 is not t2  # 瞬时


class TestGetServiceMetadata:
    """get_service_metadata 函数测试."""

    def test_get_metadata_from_injectable(self) -> None:
        """测试从 injectable 获取元数据."""

        # 准备
        @injectable(Lifetime.SINGLETON, key="test")
        class Service:
            pass

        # 执行
        metadata = get_service_metadata(Service)

        # 断言
        assert metadata is not None
        assert isinstance(metadata, ServiceMetadata)

    def test_get_metadata_returns_none_for_non_injectable(self) -> None:
        """测试非 injectable 返回 None."""

        # 准备
        class Service:
            pass

        # 执行
        metadata = get_service_metadata(Service)

        # 断言
        assert metadata is None

    def test_is_injectable_check(self) -> None:
        """测试 is_injectable 检查."""

        # 准备
        @injectable
        class Service:
            pass

        class NonService:
            pass

        # 断言
        assert is_injectable(Service)
        assert not is_injectable(NonService)


class TestDecoratorChaining:
    """装饰器链测试."""

    def test_multiple_decorators_not_needed(self) -> None:
        """测试单个装饰器足够(不需要链式装饰)."""

        # 执行
        @singleton
        class Service:
            pass

        # 断言
        metadata = get_service_metadata(Service)
        assert metadata.lifetime == Lifetime.SINGLETON
        assert is_injectable(Service)

    def test_decorator_idempotence(self) -> None:
        """测试装饰器的幂等性(多次应用结果相同)."""

        # 执行
        @singleton
        class Service:
            pass

        metadata1 = get_service_metadata(Service)
        metadata2 = get_service_metadata(Service)

        # 断言
        assert metadata1 is metadata2
        assert metadata1.lifetime == metadata2.lifetime


class TestComplexDecoratorScenarios:
    """复杂装饰器场景测试."""

    def test_large_number_of_services(self, container) -> None:
        """测试大量装饰服务的自动注册."""
        # 准备
        services = []
        for i in range(10):

            @injectable(Lifetime.TRANSIENT if i % 2 == 0 else Lifetime.SINGLETON)
            class Service:
                def __init__(self) -> None:
                    self.id = i

            services.append(Service)

        # 执行
        auto_register(container, *services)

        # 断言
        for service_class in services:
            assert container.is_registered(service_class)

    def test_mixed_decorated_and_manual_registration(self, container) -> None:
        """测试混合使用装饰器和手动注册."""

        # 准备
        @singleton
        class DecoratedService:
            pass

        class ManualService:
            pass

        # 执行
        auto_register(container, DecoratedService)
        container.register(ManualService)

        # 断言
        assert container.is_registered(DecoratedService)
        assert container.is_registered(ManualService)

        d1 = container.resolve(DecoratedService)
        d2 = container.resolve(DecoratedService)
        m1 = container.resolve(ManualService)
        m2 = container.resolve(ManualService)

        assert d1 is d2  # 装饰的是单例
        assert m1 is not m2  # 手动注册默认是瞬时
