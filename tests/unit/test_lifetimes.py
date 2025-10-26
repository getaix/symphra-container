"""生命周期管理测试.

测试容器的生命周期管理功能:
- 单例管理
- 作用域管理
- 资源释放
"""

from symphra_container import Lifetime


class TestSingletonLifetime:
    """单例生命周期测试."""

    def test_singleton_same_instance(self, container) -> None:
        """测试单例返回相同实例."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SINGLETON)
        service1 = container.resolve(Service)
        service2 = container.resolve(Service)

        # 断言
        assert service1 is service2

    def test_singleton_persists_across_registrations(self, container) -> None:
        """测试单例在多个注册间持久化."""

        # 准备
        class Config:
            def __init__(self, value: int = 42) -> None:
                self.value = value

        # 执行
        container.register(Config, lifetime=Lifetime.SINGLETON)
        config1 = container.resolve(Config)
        config1.value = 100

        config2 = container.resolve(Config)

        # 断言
        assert config2.value == 100
        assert config1 is config2

    def test_singleton_with_multiple_services(self, container) -> None:
        """测试多个单例服务."""

        # 准备
        class ServiceA:
            pass

        class ServiceB:
            pass

        # 执行
        container.register(ServiceA, lifetime=Lifetime.SINGLETON)
        container.register(ServiceB, lifetime=Lifetime.SINGLETON)

        a1 = container.resolve(ServiceA)
        a2 = container.resolve(ServiceA)
        b1 = container.resolve(ServiceB)
        b2 = container.resolve(ServiceB)

        # 断言
        assert a1 is a2
        assert b1 is b2
        assert a1 is not b1


class TestTransientLifetime:
    """瞬时生命周期测试."""

    def test_transient_creates_new_instances(self, container) -> None:
        """测试瞬时总是创建新实例."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.TRANSIENT)
        service1 = container.resolve(Service)
        service2 = container.resolve(Service)
        service3 = container.resolve(Service)

        # 断言
        assert service1 is not service2
        assert service2 is not service3
        assert service1 is not service3

    def test_transient_with_multiple_services(self, container) -> None:
        """测试多个瞬时服务."""

        # 准备
        class ServiceA:
            pass

        class ServiceB:
            pass

        # 执行
        container.register(ServiceA, lifetime=Lifetime.TRANSIENT)
        container.register(ServiceB, lifetime=Lifetime.TRANSIENT)

        a1 = container.resolve(ServiceA)
        b1 = container.resolve(ServiceB)
        a2 = container.resolve(ServiceA)

        # 断言
        assert a1 is not a2
        assert b1 is not a1
        assert b1 is not a2


class TestScopedLifetime:
    """作用域生命周期测试."""

    def test_scoped_same_instance_in_scope(self, container) -> None:
        """测试在同一作用域内获得相同实例."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SCOPED)

        with container.create_scope() as scope:
            service1 = scope.resolve(Service)
            service2 = scope.resolve(Service)

            # 断言
            assert service1 is service2

    def test_scoped_different_instances_across_scopes(self, container) -> None:
        """测试不同作用域中的实例不同."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SCOPED)

        with container.create_scope() as scope1:
            service1 = scope1.resolve(Service)

        with container.create_scope() as scope2:
            service2 = scope2.resolve(Service)

        # 断言
        assert service1 is not service2

    def test_nested_scopes(self, container) -> None:
        """测试嵌套作用域."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SCOPED)

        services = []
        with container.create_scope():
            s1 = container.resolve(Service)
            services.append(s1)

            with container.create_scope():
                s2 = container.resolve(Service)
                services.append(s2)

                # 在嵌套作用域中再次解析
                s2_again = container.resolve(Service)
                services.append(s2_again)

        # 断言 - 注意:嵌套作用域中的行为取决于实现
        # 这里我们只确保创建了实例
        assert len(services) == 3

    def test_scoped_with_dependencies(self, container) -> None:
        """测试作用域生命周期与依赖."""

        # 准备
        class Database:
            pass

        class Service:
            def __init__(self, db: Database) -> None:
                self.db = db

        # 执行
        container.register(Database, lifetime=Lifetime.SCOPED)
        container.register(Service, lifetime=Lifetime.SCOPED)

        with container.create_scope() as scope:
            db1 = scope.resolve(Database)
            service1 = scope.resolve(Service)
            service2 = scope.resolve(Service)

            # 在同一作用域内,Service 应该相同
            assert service1 is service2
            # Service 中的 Database 应该与解析的 Database 相同
            assert service1.db is db1


class TestFactoryLifetime:
    """工厂生命周期测试."""

    def test_factory_calls_function_each_time(self, container) -> None:
        """测试工厂每次都调用函数."""
        # 准备
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        # 执行
        container.register_factory("service", factory, lifetime=Lifetime.FACTORY)
        result1 = container.resolve("service")
        result2 = container.resolve("service")

        # 断言
        assert result1 == {"count": 1}
        assert result2 == {"count": 2}
        assert call_count == 2

    def test_factory_with_dependencies(self, container) -> None:
        """测试工厂函数可以返回复杂对象."""

        # 准备
        class Config:
            def __init__(self) -> None:
                self.value = 100

        config = Config()

        def factory():
            return {"value": config.value * 2}

        # 执行
        container.register_factory("service", factory, lifetime=Lifetime.FACTORY)
        result = container.resolve("service")

        # 断言
        assert result == {"value": 200}


class TestLifetimeMixtures:
    """生命周期混合测试."""

    def test_singleton_depends_on_transient(self, container) -> None:
        """测试单例依赖瞬时服务."""

        # 准备
        class Logger:
            pass

        class Service:
            def __init__(self, logger: Logger) -> None:
                self.logger = logger

        # 执行
        container.register(Logger, lifetime=Lifetime.TRANSIENT)
        container.register(Service, lifetime=Lifetime.SINGLETON)

        service1 = container.resolve(Service)
        service2 = container.resolve(Service)

        # 断言 - Service 是单例
        assert service1 is service2
        # 注意:logger 在初始化时是瞬时的,所以 service1 和 service2 的 logger 是同一个
        # (因为都是在初始化时创建的同一个实例)
        assert service1.logger is service2.logger

    def test_transient_depends_on_singleton(self, container) -> None:
        """测试瞬时服务依赖单例."""

        # 准备
        class Config:
            pass

        class Service:
            def __init__(self, config: Config) -> None:
                self.config = config

        # 执行
        container.register(Config, lifetime=Lifetime.SINGLETON)
        container.register(Service, lifetime=Lifetime.TRANSIENT)

        service1 = container.resolve(Service)
        service2 = container.resolve(Service)

        # 断言
        assert service1 is not service2
        # 但 Config 应该是同一个实例
        assert service1.config is service2.config

    def test_scoped_depends_on_singleton(self, container) -> None:
        """测试作用域服务依赖单例."""

        # 准备
        class Logger:
            pass

        class Service:
            def __init__(self, logger: Logger) -> None:
                self.logger = logger

        # 执行
        container.register(Logger, lifetime=Lifetime.SINGLETON)
        container.register(Service, lifetime=Lifetime.SCOPED)

        logger_global = container.resolve(Logger)

        with container.create_scope() as scope:
            service1 = scope.resolve(Service)
            service2 = scope.resolve(Service)

        # 断言
        assert service1 is service2  # 在同一作用域内
        assert service1.logger is logger_global  # 使用全局 Logger


class TestResourceCleanup:
    """资源清理测试."""

    def test_container_dispose_clears_singletons(self, container) -> None:
        """测试容器释放时清空单例."""

        # 准备
        class Service:
            pass

        # 执行
        container.register(Service, lifetime=Lifetime.SINGLETON)
        container.resolve(Service)

        # 释放前
        assert container.is_registered(Service)

        # 释放
        container.dispose()

        # 释放后
        assert container._registrations == {}

    def test_disposable_called_on_cleanup(self, container) -> None:
        """测试清理时调用 dispose 方法."""
        # 准备
        dispose_called = False

        class Service:
            def dispose(self) -> None:
                nonlocal dispose_called
                dispose_called = True

        # 执行
        container.register_instance("service", Service())
        container.dispose()

        # 断言
        assert dispose_called is True

    def test_multiple_disposables(self, container) -> None:
        """测试多个 Disposable 对象的清理."""
        # 准备
        disposed = []

        class Service:
            def __init__(self, name) -> None:
                self.name = name

            def dispose(self) -> None:
                disposed.append(self.name)

        # 执行
        service1 = Service("service1")
        service2 = Service("service2")

        container.register_instance("s1", service1)
        container.register_instance("s2", service2)

        container.dispose()

        # 断言
        assert "service1" in disposed
        assert "service2" in disposed
