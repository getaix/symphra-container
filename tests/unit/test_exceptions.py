"""异常类测试.

测试所有自定义异常类型.
"""

from symphra_container.exceptions import (
    CircularDependencyError,
    ContainerException,
    FactoryError,
    InterceptorError,
    InvalidConfigurationError,
    OptionalDependencyError,
    RegistrationError,
    ResolutionError,
    ScopeNotActiveError,
    ServiceNotFoundError,
    TypeMismatchError,
)


class TestContainerException:
    """ContainerException 测试."""

    def test_create_with_message(self) -> None:
        """测试创建异常."""
        exc = ContainerException("Test error")
        assert str(exc) == "ContainerException: Test error"

    def test_create_with_service_key(self) -> None:
        """测试带服务键的异常."""
        exc = ContainerException("Test error", "MyService")
        assert "MyService" in str(exc)


class TestServiceNotFoundError:
    """ServiceNotFoundError 测试."""

    def test_service_not_found(self) -> None:
        """测试服务未找到异常."""
        exc = ServiceNotFoundError("UserService")
        assert "UserService" in str(exc)
        assert "not found" in str(exc)

    def test_with_registered_services(self) -> None:
        """测试显示已注册服务."""
        exc = ServiceNotFoundError("NewService", ["ServiceA", "ServiceB"])
        assert "NewService" in str(exc)


class TestCircularDependencyError:
    """CircularDependencyError 测试."""

    def test_circular_dependency(self) -> None:
        """测试循环依赖异常."""
        exc = CircularDependencyError("ServiceA", ["ServiceA", "ServiceB"])
        assert "ServiceA" in str(exc)
        assert "Circular" in str(exc)


class TestTypeMismatchError:
    """TypeMismatchError 测试."""

    def test_type_mismatch(self) -> None:
        """测试类型不匹配异常."""

        class ExpectedType:
            pass

        class ActualType:
            pass

        exc = TypeMismatchError("service", ExpectedType, ActualType)
        assert "Type mismatch" in str(exc)


class TestRegistrationError:
    """RegistrationError 测试."""

    def test_registration_error(self) -> None:
        """测试注册错误."""
        exc = RegistrationError("MyService", "Already registered")
        assert "MyService" in str(exc)
        assert "Already registered" in str(exc)


class TestResolutionError:
    """ResolutionError 测试."""

    def test_resolution_error_without_cause(self) -> None:
        """测试解析错误(无原因)."""
        exc = ResolutionError("MyService")
        assert "MyService" in str(exc)
        assert "Failed to resolve" in str(exc)

    def test_resolution_error_with_cause(self) -> None:
        """测试解析错误(有原因)."""
        cause = ValueError("Test cause")
        exc = ResolutionError("MyService", cause)
        assert "MyService" in str(exc)
        assert "Test cause" in str(exc)


class TestInvalidConfigurationError:
    """InvalidConfigurationError 测试."""

    def test_invalid_configuration(self) -> None:
        """测试无效配置异常."""
        exc = InvalidConfigurationError("Invalid setting")
        assert "Invalid configuration" in str(exc)
        assert "Invalid setting" in str(exc)


class TestOptionalDependencyError:
    """OptionalDependencyError 测试."""

    def test_optional_dependency_error(self) -> None:
        """测试可选依赖错误."""
        exc = OptionalDependencyError("MainService", "OptionalService")
        assert "MainService" in str(exc)
        assert "OptionalService" in str(exc)


class TestScopeNotActiveError:
    """ScopeNotActiveError 测试."""

    def test_scope_not_active(self) -> None:
        """测试作用域未激活异常."""
        exc = ScopeNotActiveError()
        assert "not active" in str(exc).lower()

    def test_custom_message(self) -> None:
        """测试自定义消息."""
        exc = ScopeNotActiveError("Custom message")
        assert "Custom message" in str(exc)


class TestInterceptorError:
    """InterceptorError 测试."""

    def test_interceptor_error(self) -> None:
        """测试拦截器错误."""
        exc = InterceptorError("MyService", "before_interceptor")
        assert "MyService" in str(exc)
        assert "before_interceptor" in str(exc)

    def test_with_original_exception(self) -> None:
        """测试带原始异常."""
        cause = RuntimeError("Original error")
        exc = InterceptorError("MyService", "my_interceptor", cause)
        assert "MyService" in str(exc)
        assert "Original error" in str(exc)


class TestFactoryError:
    """FactoryError 测试."""

    def test_factory_error(self) -> None:
        """测试工厂错误."""
        exc = FactoryError("MyService")
        assert "MyService" in str(exc)
        assert "Factory" in str(exc)

    def test_with_original_exception(self) -> None:
        """测试带原始异常."""
        cause = ValueError("Factory failed")
        exc = FactoryError("MyService", cause)
        assert "MyService" in str(exc)
        assert "Factory failed" in str(exc)
