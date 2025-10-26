#!/bin/bash
# Symphra Container - 项目启动脚本
# 使用: bash STARTUP_GUIDE.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 工具函数
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查 Python 版本
check_python() {
    print_header "Step 1: 检查 Python 版本"

    if ! command -v python3 &> /dev/null; then
        print_error "未找到 Python 3，请先安装 Python 3.9 或更高版本"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "找到 Python 版本: $PYTHON_VERSION"

    # 检查版本号 >= 3.9
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || [ "$MAJOR" -eq 3 -a "$MINOR" -lt 9 ]; then
        print_error "需要 Python 3.9 或更高版本，当前版本 $PYTHON_VERSION"
        exit 1
    fi
}

# 创建虚拟环境
setup_venv() {
    print_header "Step 2: 创建 Python 虚拟环境"

    if [ -d "venv" ]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        python3 -m venv venv
        print_success "虚拟环境创建成功"
    fi

    # 激活虚拟环境
    source venv/bin/activate
    print_success "虚拟环境已激活"
}

# 升级 pip
upgrade_pip() {
    print_header "Step 3: 升级 pip"

    pip install --upgrade pip setuptools wheel
    print_success "pip 升级完成"
}

# 创建项目结构
create_structure() {
    print_header "Step 4: 创建项目目录结构"

    # 源码目录
    mkdir -p src/symphra_container/{injection,lifetimes,circular,decorators,scopes,integrations,testing,utils}
    mkdir -p src/symphra_container/integrations
    mkdir -p src/symphra_container/config

    # 测试目录
    mkdir -p tests/{unit,integration,performance}
    mkdir -p tests/fixtures

    # 文档目录
    mkdir -p docs/{guide,api,integrations,tools,examples}

    # 基准测试目录
    mkdir -p benchmarks

    # 脚本目录
    mkdir -p scripts

    print_success "目录结构创建完成"
}

# 创建核心文件
create_core_files() {
    print_header "Step 5: 创建核心源文件"

    # __init__.py 文件
    for dir in src/symphra_container src/symphra_container/{injection,lifetimes,circular,decorators,scopes,integrations,config} tests tests/{unit,integration,performance}; do
        touch "$dir/__init__.py"
    done

    # py.typed 标记文件（PEP 561）
    touch src/symphra_container/py.typed

    # 核心模块文件
    cat > src/symphra_container/types.py << 'EOF'
"""Symphra Container - Core Type Definitions

This module defines the fundamental types and protocols used throughout
the container system.
"""

from typing import TypeVar, Generic, Protocol, Union, Optional, Callable, Any, Type, Dict, List, Set
from enum import Enum
import threading
from abc import ABC, abstractmethod

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)

# Service key can be either a type or a string
ServiceKey = Union[Type[T], str]


class Lifetime(str, Enum):
    """Service lifetime enumeration."""
    SINGLETON = "singleton"      # Single instance for entire application
    TRANSIENT = "transient"      # New instance every time
    SCOPED = "scoped"            # Single instance per scope
    FACTORY = "factory"          # Created via factory function


class ProviderType(str, Enum):
    """Service provider type enumeration."""
    CLASS = "class"              # Constructor injection
    FACTORY = "factory"          # Factory function
    INSTANCE = "instance"        # Direct instance
    VALUE = "value"              # Configuration value


class ServiceDescriptor:
    """Describes a registered service."""

    def __init__(self,
                 service_type: ServiceKey,
                 impl_type: Optional[Type] = None,
                 factory: Optional[Callable] = None,
                 instance: Optional[Any] = None,
                 lifetime: Lifetime = Lifetime.SINGLETON,
                 lazy: bool = False,
                 tags: Optional[List[str]] = None,
                 categories: Optional[List[str]] = None):
        self.service_type = service_type
        self.impl_type = impl_type
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        self.lazy = lazy
        self.tags = set(tags or [])
        self.categories = set(categories or [])
        self.metadata: Dict[str, Any] = {}

    @property
    def provider_type(self) -> ProviderType:
        """Determine the provider type."""
        if self.instance is not None:
            return ProviderType.INSTANCE
        elif self.factory is not None:
            return ProviderType.FACTORY
        else:
            return ProviderType.CLASS


# ============ Protocols ============

class Provider(Protocol[T_co]):
    """Service provider protocol."""

    def provide(self) -> T_co:
        """Provide an instance of the service."""
        ...


class Resolver(Protocol):
    """Dependency resolver protocol."""

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service and its dependencies."""
        ...


class LifetimeManager(Protocol):
    """Lifetime manager protocol."""

    def get_instance(self, factory: Callable[[], T]) -> T:
        """Get or create an instance based on lifetime."""
        ...

    def dispose(self) -> None:
        """Dispose resources managed by this lifetime manager."""
        ...


class Disposable(Protocol):
    """Disposable resource protocol."""

    def dispose(self) -> None:
        """Dispose the resource."""
        ...


class AsyncDisposable(Protocol):
    """Async disposable resource protocol."""

    async def dispose_async(self) -> None:
        """Asynchronously dispose the resource."""
        ...


class Interceptor(Protocol):
    """Service resolution interceptor protocol."""

    def before_resolve(self, key: ServiceKey) -> None:
        """Hook called before resolving a service."""
        ...

    def after_resolve(self, key: ServiceKey, instance: Any) -> Any:
        """Hook called after resolving a service. Can modify the instance."""
        ...

    def on_error(self, key: ServiceKey, error: Exception) -> None:
        """Hook called when resolution fails."""
        ...


class Injector(Protocol):
    """Custom dependency injector protocol."""

    def can_inject(self, param_type: Type) -> bool:
        """Check if this injector can inject the given type."""
        ...

    def inject(self, container: "Container", param_type: Type) -> Any:  # type: ignore
        """Inject a dependency of the given type."""
        ...
EOF

    print_success "核心类型定义文件创建完成"
}

# 创建异常定义文件
create_exceptions() {
    print_header "Step 6: 创建异常定义文件"

    cat > src/symphra_container/exceptions.py << 'EOF'
"""Symphra Container - Exception Definitions"""

from typing import List, Optional, Any


class ContainerException(Exception):
    """Base exception for container errors."""
    pass


class ServiceNotFoundError(ContainerException):
    """Raised when a service is not found in the container."""

    def __init__(self, key: Any, available_services: List[str],
                 similar_services: Optional[List[str]] = None):
        self.key = key
        self.available_services = available_services
        self.similar_services = similar_services or []

        msg = f"\n❌ Service {key!r} not found\n"
        msg += f"\n📋 Available services ({len(available_services)}):\n"
        for svc in available_services[:10]:
            msg += f"   - {svc}\n"

        if len(available_services) > 10:
            msg += f"   ... and {len(available_services) - 10} more\n"

        if self.similar_services:
            msg += f"\n💡 Did you mean?\n"
            for svc in self.similar_services:
                msg += f"   - {svc}\n"

        super().__init__(msg)


class CircularDependencyError(ContainerException):
    """Raised when a circular dependency is detected."""

    def __init__(self, dependency_chain: List[str]):
        self.dependency_chain = dependency_chain
        chain_str = " -> ".join(dependency_chain)
        msg = f"\n❌ Circular dependency detected:\n{chain_str}\n\n"
        msg += "💡 Solutions:\n"
        msg += "   1. Use Lazy[T] to delay resolution\n"
        msg += "   2. Use property or method injection\n"
        msg += "   3. Restructure your dependencies\n"
        super().__init__(msg)


class InvalidServiceError(ContainerException):
    """Raised when a service definition is invalid."""
    pass


class RegistrationError(ContainerException):
    """Raised when service registration fails."""
    pass


class ResolutionError(ContainerException):
    """Raised when service resolution fails."""
    pass
EOF

    print_success "异常定义文件创建完成"
}

# 创建基础容器文件
create_container() {
    print_header "Step 7: 创建基础容器文件"

    cat > src/symphra_container/container.py << 'EOF'
"""Symphra Container - Main Container Implementation"""

from typing import TypeVar, Generic, Optional, Dict, Any, List, Type, Union, Callable
from abc import ABC, abstractmethod
import threading

from .types import ServiceKey, Lifetime, ServiceDescriptor
from .exceptions import ServiceNotFoundError, RegistrationError

T = TypeVar("T")


class Container:
    """Main dependency injection container."""

    def __init__(self, name: Optional[str] = None):
        """Initialize the container.

        Args:
            name: Optional name for debugging purposes.
        """
        self.name = name or "DefaultContainer"
        self._registry: Dict[ServiceKey, ServiceDescriptor] = {}
        self._lock = threading.RLock()
        self._interceptors: List[Any] = []

    def register(self,
                 service_type: Union[Type[T], str],
                 impl: Optional[Union[Type[T], Callable]] = None,
                 *,
                 lifetime: Lifetime = Lifetime.SINGLETON,
                 override: bool = False,
                 lazy: bool = False,
                 tags: Optional[List[str]] = None,
                 categories: Optional[List[str]] = None) -> None:
        """Register a service in the container.

        Args:
            service_type: The service type (class or string key)
            impl: Implementation (class or factory function)
            lifetime: Service lifetime mode
            override: Whether to override existing registration
            lazy: Whether to lazily initialize Singleton
            tags: Service tags for categorization
            categories: Service categories for grouping

        Raises:
            RegistrationError: If service already registered and override=False
        """
        with self._lock:
            if service_type in self._registry and not override:
                raise RegistrationError(
                    f"Service {service_type} already registered. Use override=True to replace it."
                )

            if impl is None:
                impl = service_type

            descriptor = ServiceDescriptor(
                service_type=service_type,
                impl_type=impl if isinstance(impl, type) else None,
                factory=impl if callable(impl) and not isinstance(impl, type) else None,
                lifetime=lifetime,
                lazy=lazy,
                tags=tags,
                categories=categories
            )

            self._registry[service_type] = descriptor

    def resolve(self, key: ServiceKey[T]) -> T:
        """Resolve a service from the container.

        Args:
            key: Service key (type or string)

        Returns:
            The resolved service instance

        Raises:
            ServiceNotFoundError: If service is not registered
        """
        if key not in self._registry:
            available = list(self._registry.keys())
            similar = self._find_similar(str(key), [str(k) for k in available])
            raise ServiceNotFoundError(key, [str(k) for k in available], similar)

        descriptor = self._registry[key]

        # Call interceptors
        for interceptor in self._interceptors:
            if hasattr(interceptor, 'before_resolve'):
                interceptor.before_resolve(key)

        try:
            # Simple implementation - TODO: expand with full logic
            instance = descriptor.instance or object()

            # Call interceptors after resolution
            for interceptor in self._interceptors:
                if hasattr(interceptor, 'after_resolve'):
                    instance = interceptor.after_resolve(key, instance)

            return instance
        except Exception as e:
            for interceptor in self._interceptors:
                if hasattr(interceptor, 'on_error'):
                    interceptor.on_error(key, e)
            raise

    def resolve_optional(self, key: ServiceKey[T]) -> Optional[T]:
        """Try to resolve a service, returning None if not found.

        Args:
            key: Service key (type or string)

        Returns:
            The resolved service instance or None
        """
        try:
            return self.resolve(key)
        except ServiceNotFoundError:
            return None

    def __getitem__(self, key: ServiceKey[T]) -> T:
        """Shorthand for resolve using bracket notation."""
        return self.resolve(key)

    def __setitem__(self, key: ServiceKey[T], impl: T) -> None:
        """Shorthand for register_instance using bracket notation."""
        self.register_instance(key, impl)

    def register_instance(self, key: Union[Type[T], str], instance: T) -> None:
        """Register a service instance.

        Args:
            key: Service key
            instance: Service instance
        """
        descriptor = ServiceDescriptor(
            service_type=key,
            instance=instance,
            lifetime=Lifetime.SINGLETON
        )
        with self._lock:
            self._registry[key] = descriptor

    def register_value(self, key: str, value: Any) -> None:
        """Register a configuration value.

        Args:
            key: Value key
            value: Value to register
        """
        self.register_instance(key, value)

    def unregister(self, key: ServiceKey) -> None:
        """Unregister a service.

        Args:
            key: Service key to unregister
        """
        with self._lock:
            if key in self._registry:
                del self._registry[key]

    def has(self, key: ServiceKey) -> bool:
        """Check if a service is registered.

        Args:
            key: Service key

        Returns:
            True if service is registered, False otherwise
        """
        return key in self._registry

    def add_interceptor(self, interceptor: Any) -> None:
        """Add a service resolution interceptor.

        Args:
            interceptor: Interceptor instance
        """
        self._interceptors.append(interceptor)

    def get_available_services(self) -> List[str]:
        """Get list of all available services.

        Returns:
            List of service keys as strings
        """
        return [str(k) for k in self._registry.keys()]

    @staticmethod
    def _find_similar(target: str, candidates: List[str], threshold: float = 0.6) -> List[str]:
        """Find similar strings using basic similarity metric.

        Args:
            target: Target string
            candidates: List of candidate strings
            threshold: Similarity threshold (0-1)

        Returns:
            List of similar strings, sorted by similarity
        """
        from difflib import SequenceMatcher

        similar = []
        for candidate in candidates:
            ratio = SequenceMatcher(None, target.lower(), candidate.lower()).ratio()
            if ratio >= threshold:
                similar.append((candidate, ratio))

        return [s[0] for s in sorted(similar, key=lambda x: x[1], reverse=True)]
EOF

    print_success "基础容器文件创建完成"
}

# 创建测试文件
create_tests() {
    print_header "Step 8: 创建基础测试文件"

    cat > tests/unit/test_container_basic.py << 'EOF'
"""Basic container tests."""

import pytest
from symphra_container import Container, Lifetime
from symphra_container.exceptions import ServiceNotFoundError


class TestContainerBasic:
    """Basic container functionality tests."""

    def test_register_and_resolve_instance(self):
        """Test basic service registration and resolution."""
        container = Container()
        test_obj = object()

        container.register_instance("test_service", test_obj)
        resolved = container.resolve("test_service")

        assert resolved is test_obj

    def test_resolve_nonexistent_service(self):
        """Test that resolving non-existent service raises error."""
        container = Container()

        with pytest.raises(ServiceNotFoundError):
            container.resolve("non_existent")

    def test_resolve_optional_returns_none(self):
        """Test that resolve_optional returns None for missing service."""
        container = Container()

        result = container.resolve_optional("missing")
        assert result is None

    def test_has_service(self):
        """Test checking if service is registered."""
        container = Container()

        assert not container.has("test")
        container.register_instance("test", "value")
        assert container.has("test")

    def test_bracket_notation_resolve(self):
        """Test bracket notation for resolve."""
        container = Container()
        container.register_instance("service", "value")

        assert container["service"] == "value"

    def test_bracket_notation_register(self):
        """Test bracket notation for register_instance."""
        container = Container()
        container["service"] = "value"

        assert container.resolve("service") == "value"

    def test_get_available_services(self):
        """Test getting list of available services."""
        container = Container()
        container.register_instance("service1", "value1")
        container.register_instance("service2", "value2")

        services = container.get_available_services()
        assert "service1" in services
        assert "service2" in services

    def test_unregister_service(self):
        """Test unregistering a service."""
        container = Container()
        container.register_instance("service", "value")
        assert container.has("service")

        container.unregister("service")
        assert not container.has("service")
EOF

    print_success "基础测试文件创建完成"
}

# 创建 pyproject.toml
create_pyproject() {
    print_header "Step 9: 创建 pyproject.toml 配置文件"

    cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=65", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "symphra-container"
version = "0.1.0"
description = "Enterprise-grade Python dependency injection container"
readme = "README.md"
requires-python = ">=3.9"
authors = [
    {name = "Your Name", email = "your@email.com"},
]
license = {text = "MIT"}
keywords = ["dependency-injection", "di", "container", "ioc"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
    "black>=23.0",
    "isort>=5.12",
]
docs = [
    "sphinx>=6.0",
    "sphinx-rtd-theme>=1.2",
]
frameworks = [
    "fastapi>=0.100",
    "flask>=2.3",
]

[tool.setuptools]
packages = ["symphra_container"]
package-dir = {"" = "src"}

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
addopts = "--cov=src/symphra_container --cov-report=html --cov-report=term-missing"

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimplemented = true
no_implicit_optional = true

[tool.black]
line-length = 100
target-version = ['py39']

[tool.ruff]
line-length = 100
target-version = "py39"
EOF

    print_success "pyproject.toml 创建完成"
}

# 安装依赖
install_dependencies() {
    print_header "Step 10: 安装项目依赖"

    pip install -e ".[dev]"
    print_success "依赖安装完成"
}

# 运行初始测试
run_initial_tests() {
    print_header "Step 11: 运行初始测试"

    pytest tests/unit/test_container_basic.py -v
    print_success "初始测试通过"
}

# 主函数
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   Symphra Container - 项目启动脚本                         ║"
    echo "║   Enterprise-grade Python Dependency Injection Container  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_python
    setup_venv
    upgrade_pip
    create_structure
    create_core_files
    create_exceptions
    create_container
    create_tests
    create_pyproject
    install_dependencies
    run_initial_tests

    # 最后的总结
    echo -e "\n"
    print_header "项目启动完成！🎉"

    echo -e "${GREEN}✅ 环境已准备就绪${NC}"
    echo -e "\n${BLUE}后续步骤:${NC}"
    echo "1. 激活虚拟环境: source venv/bin/activate"
    echo "2. 查看项目文档: cat API_DESIGN.md"
    echo "3. 查看实施规划: cat INTEGRATED_ROADMAP.md"
    echo "4. 开始第一阶段开发: 参考 IMPLEMENTATION_CHECKLIST.md"
    echo ""
    echo -e "${BLUE}运行测试:${NC}"
    echo "  pytest tests/ -v                    # 运行所有测试"
    echo "  pytest tests/ --cov                 # 运行带覆盖率报告"
    echo "  mypy src/symphra_container --strict # 类型检查"
    echo ""
    echo -e "${BLUE}代码质量:${NC}"
    echo "  black src/ tests/                   # 代码格式化"
    echo "  ruff check src/ tests/              # Lint 检查"
    echo ""
}

# 错误处理
trap 'print_error "脚本执行失败"; exit 1' ERR

# 运行主函数
main
