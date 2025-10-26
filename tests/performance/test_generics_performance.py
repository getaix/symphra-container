"""泛型支持性能测试."""

from typing import Generic, TypeVar

import pytest

from symphra_container import Container, Lifetime
from symphra_container.generics import GenericKey, register_generic, resolve_generic

T = TypeVar("T")


class Repository(Generic[T]):
    """通用仓储."""

    def get(self, entity_id: int) -> T:
        """获取实体."""
        raise NotImplementedError


class Entity:
    """实体基类."""

    def __init__(self, entity_id: int) -> None:
        self.entity_id = entity_id


# 创建多个实体类型用于测试
class User(Entity):
    """用户实体."""



class Order(Entity):
    """订单实体."""



class Product(Entity):
    """产品实体."""



class Customer(Entity):
    """客户实体."""



class Invoice(Entity):
    """发票实体."""



# 对应的仓储实现
class UserRepository(Repository[User]):
    """用户仓储."""

    def get(self, entity_id: int) -> User:
        return User(entity_id)


class OrderRepository(Repository[Order]):
    """订单仓储."""

    def get(self, entity_id: int) -> Order:
        return Order(entity_id)


class ProductRepository(Repository[Product]):
    """产品仓储."""

    def get(self, entity_id: int) -> Product:
        return Product(entity_id)


class CustomerRepository(Repository[Customer]):
    """客户仓储."""

    def get(self, entity_id: int) -> Customer:
        return Customer(entity_id)


class InvoiceRepository(Repository[Invoice]):
    """发票仓储."""

    def get(self, entity_id: int) -> Invoice:
        return Invoice(entity_id)


@pytest.fixture
def container_with_generics() -> Container:
    """创建包含多个泛型服务的容器."""
    container = Container()

    # 注册多个泛型服务
    register_generic(container, Repository[User], UserRepository, lifetime=Lifetime.SINGLETON)
    register_generic(container, Repository[Order], OrderRepository, lifetime=Lifetime.SINGLETON)
    register_generic(container, Repository[Product], ProductRepository, lifetime=Lifetime.TRANSIENT)
    register_generic(container, Repository[Customer], CustomerRepository, lifetime=Lifetime.TRANSIENT)
    register_generic(container, Repository[Invoice], InvoiceRepository, lifetime=Lifetime.SCOPED)

    return container


def test_generic_key_creation_performance(benchmark) -> None:
    """测试 GenericKey 创建性能."""

    def create_keys() -> list[GenericKey]:
        return [
            GenericKey(Repository, (User,)),
            GenericKey(Repository, (Order,)),
            GenericKey(Repository, (Product,)),
            GenericKey(Repository, (Customer,)),
            GenericKey(Repository, (Invoice,)),
        ]

    result = benchmark(create_keys)
    assert len(result) == 5


def test_generic_key_equality_performance(benchmark) -> None:
    """测试 GenericKey 相等性检查性能."""
    key1 = GenericKey(Repository, (User,))
    key2 = GenericKey(Repository, (User,))
    key3 = GenericKey(Repository, (Order,))

    def check_equality() -> tuple[bool, bool, bool]:
        return (key1 == key2, key1 == key3, key1 == key1)

    result = benchmark(check_equality)
    assert result == (True, False, True)


def test_generic_key_hash_performance(benchmark) -> None:
    """测试 GenericKey 哈希性能."""
    keys = [
        GenericKey(Repository, (User,)),
        GenericKey(Repository, (Order,)),
        GenericKey(Repository, (Product,)),
        GenericKey(Repository, (Customer,)),
        GenericKey(Repository, (Invoice,)),
    ]

    def hash_keys() -> set[int]:
        return {hash(key) for key in keys}

    result = benchmark(hash_keys)
    assert len(result) == 5


def test_register_generic_performance(benchmark) -> None:
    """测试泛型服务注册性能."""

    def register_services() -> Container:
        container = Container()
        register_generic(container, Repository[User], UserRepository, lifetime=Lifetime.SINGLETON)
        register_generic(container, Repository[Order], OrderRepository, lifetime=Lifetime.SINGLETON)
        register_generic(container, Repository[Product], ProductRepository, lifetime=Lifetime.TRANSIENT)
        register_generic(container, Repository[Customer], CustomerRepository, lifetime=Lifetime.TRANSIENT)
        register_generic(container, Repository[Invoice], InvoiceRepository, lifetime=Lifetime.SCOPED)
        return container

    result = benchmark(register_services)
    assert len(result._registrations) == 5


def test_resolve_generic_singleton_performance(benchmark, container_with_generics) -> None:
    """测试解析单例泛型服务性能."""

    def resolve_service() -> UserRepository:
        return resolve_generic(container_with_generics, Repository[User])

    result = benchmark(resolve_service)
    assert isinstance(result, UserRepository)


def test_resolve_generic_transient_performance(benchmark, container_with_generics) -> None:
    """测试解析瞬态泛型服务性能."""

    def resolve_service() -> ProductRepository:
        return resolve_generic(container_with_generics, Repository[Product])

    result = benchmark(resolve_service)
    assert isinstance(result, ProductRepository)


def test_resolve_multiple_generics_performance(benchmark, container_with_generics) -> None:
    """测试批量解析多个泛型服务性能."""

    def resolve_multiple() -> tuple:
        user_repo = resolve_generic(container_with_generics, Repository[User])
        order_repo = resolve_generic(container_with_generics, Repository[Order])
        product_repo = resolve_generic(container_with_generics, Repository[Product])
        customer_repo = resolve_generic(container_with_generics, Repository[Customer])
        invoice_repo = resolve_generic(container_with_generics, Repository[Invoice])
        return (user_repo, order_repo, product_repo, customer_repo, invoice_repo)

    result = benchmark(resolve_multiple)
    assert len(result) == 5


def test_generic_key_as_dict_key_performance(benchmark) -> None:
    """测试 GenericKey 作为字典键的性能."""
    keys = [
        GenericKey(Repository, (User,)),
        GenericKey(Repository, (Order,)),
        GenericKey(Repository, (Product,)),
        GenericKey(Repository, (Customer,)),
        GenericKey(Repository, (Invoice,)),
    ]

    def use_as_dict_keys() -> dict:
        data = {}
        for i, key in enumerate(keys):
            data[key] = f"value_{i}"
        # 执行查找
        for key in keys:
            _ = data[key]
        return data

    result = benchmark(use_as_dict_keys)
    assert len(result) == 5


def test_large_scale_generic_registration(benchmark) -> None:
    """测试大规模泛型服务注册性能."""
    # 创建100个不同的实体类型
    entity_types = [type(f"Entity{i}", (Entity,), {}) for i in range(100)]

    # 创建对应的仓储类型
    repo_types = [
        type(
            f"Repository{i}",
            (Repository,),
            {
                "get": lambda self, entity_id, et=et: et(entity_id),
            },
        )
        for i, et in enumerate(entity_types)
    ]

    def register_many_generics() -> Container:
        container = Container()
        for entity_type, repo_type in zip(entity_types, repo_types, strict=False):
            # 注意: 这里无法使用真正的泛型语法，因为类型是动态创建的
            # 所以我们直接使用 GenericKey
            key = GenericKey(Repository, (entity_type,))
            container.register(repo_type, key=key, lifetime=Lifetime.TRANSIENT)
        return container

    result = benchmark(register_many_generics)
    assert len(result._registrations) == 100


def test_generic_resolution_with_dependencies_performance(benchmark) -> None:
    """测试带依赖的泛型服务解析性能."""

    class Logger:
        """日志服务."""


    class Database:
        """数据库服务."""

        def __init__(self, logger: Logger) -> None:
            self.logger = logger

    class ComplexRepository(Repository[User]):
        """复杂仓储 (有依赖)."""

        def __init__(self, db: Database, logger: Logger) -> None:
            self.db = db
            self.logger = logger

        def get(self, entity_id: int) -> User:
            return User(entity_id)

    def setup_and_resolve() -> ComplexRepository:
        container = Container()
        container.register(Logger, lifetime=Lifetime.SINGLETON)
        container.register(Database, lifetime=Lifetime.SINGLETON)
        register_generic(container, Repository[User], ComplexRepository, lifetime=Lifetime.TRANSIENT)
        return resolve_generic(container, Repository[User])

    result = benchmark(setup_and_resolve)
    assert isinstance(result, ComplexRepository)


def test_concurrent_generic_resolution_simulation(benchmark, container_with_generics) -> None:
    """模拟并发场景下的泛型服务解析性能."""

    def simulate_concurrent_access() -> list:
        results = []
        # 模拟10个并发请求
        for _ in range(10):
            user_repo = resolve_generic(container_with_generics, Repository[User])
            order_repo = resolve_generic(container_with_generics, Repository[Order])
            product_repo = resolve_generic(container_with_generics, Repository[Product])
            results.extend([user_repo, order_repo, product_repo])
        return results

    result = benchmark(simulate_concurrent_access)
    assert len(result) == 30
