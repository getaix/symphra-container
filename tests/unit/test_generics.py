"""测试泛型类型支持."""

from typing import Generic, TypeVar

import pytest

from symphra_container import Container, Lifetime
from symphra_container.generics import (
    GenericKey,
    is_generic_type,
    register_generic,
    resolve_generic,
)

T = TypeVar("T")


class Repository(Generic[T]):
    """通用仓储接口."""

    def get(self, id: int) -> T:
        """获取实体."""
        raise NotImplementedError


class User:
    """用户实体."""

    def __init__(self, name: str = "Test User") -> None:
        self.name = name


class Order:
    """订单实体."""

    def __init__(self, order_id: str = "ORD-001") -> None:
        self.order_id = order_id


class UserRepository(Repository[User]):
    """用户仓储实现."""

    def get(self, id: int) -> User:
        return User(f"User {id}")


class OrderRepository(Repository[Order]):
    """订单仓储实现."""

    def get(self, id: int) -> Order:
        return Order(f"ORD-{id}")


def test_generic_key_equality():
    """测试泛型键的相等性."""
    key1 = GenericKey(Repository, (User,))
    key2 = GenericKey(Repository, (User,))
    key3 = GenericKey(Repository, (Order,))

    assert key1 == key2
    assert key1 != key3
    assert hash(key1) == hash(key2)
    assert hash(key1) != hash(key3)


def test_generic_key_repr():
    """测试泛型键的字符串表示."""
    key = GenericKey(Repository, (User,))
    assert "Repository[User]" in repr(key)


def test_register_generic_with_implementation():
    """测试注册泛型服务 (使用实现类)."""
    container = Container()

    # 注册不同类型参数的服务
    register_generic(container, Repository[User], UserRepository)
    register_generic(container, Repository[Order], OrderRepository)

    # 解析服务
    user_repo = resolve_generic(container, Repository[User])
    order_repo = resolve_generic(container, Repository[Order])

    # 验证
    assert isinstance(user_repo, UserRepository)
    assert isinstance(order_repo, OrderRepository)
    assert user_repo is not order_repo

    # 验证功能
    user = user_repo.get(1)
    order = order_repo.get(1)
    assert user.name == "User 1"
    assert order.order_id == "ORD-1"


def test_register_generic_with_factory():
    """测试注册泛型服务 (使用工厂函数)."""
    container = Container()

    # 使用工厂函数注册
    register_generic(container, Repository[User], factory=lambda: UserRepository(), lifetime=Lifetime.SINGLETON)

    # 解析服务
    repo1 = resolve_generic(container, Repository[User])
    repo2 = resolve_generic(container, Repository[User])

    # 验证单例
    assert repo1 is repo2


def test_register_generic_with_lifetime():
    """测试泛型服务的生命周期."""
    container = Container()

    # 注册为瞬态
    register_generic(container, Repository[User], UserRepository, lifetime=Lifetime.TRANSIENT)

    # 每次解析都是新实例
    repo1 = resolve_generic(container, Repository[User])
    repo2 = resolve_generic(container, Repository[User])
    assert repo1 is not repo2


def test_register_generic_invalid_type():
    """测试注册非泛型类型时抛出异常."""
    container = Container()

    with pytest.raises(ValueError, match="Not a valid generic type"):
        register_generic(container, User, User)


def test_register_generic_without_implementation_or_factory():
    """测试既没有实现类也没有工厂函数时抛出异常."""
    container = Container()

    with pytest.raises(ValueError, match="Either implementation or factory must be provided"):
        register_generic(container, Repository[User])


def test_resolve_generic_not_registered():
    """测试解析未注册的泛型服务."""
    container = Container()

    with pytest.raises(Exception):  # ServiceNotFoundError
        resolve_generic(container, Repository[User])


def test_resolve_generic_invalid_type():
    """测试解析非泛型类型时抛出异常."""
    container = Container()

    with pytest.raises(ValueError, match="Not a valid generic type"):
        resolve_generic(container, User)


def test_is_generic_type():
    """测试泛型类型检查."""
    assert is_generic_type(Repository[User]) is True
    assert is_generic_type(Repository[Order]) is True
    assert is_generic_type(Repository) is False
    assert is_generic_type(User) is False
    assert is_generic_type(int) is False


def test_multiple_type_parameters():
    """测试多个类型参数的泛型."""
    T1 = TypeVar("T1")
    T2 = TypeVar("T2")

    class Mapper(Generic[T1, T2]):
        """映射器."""


    class UserOrderMapper(Mapper[User, Order]):
        """用户订单映射器."""


    container = Container()
    register_generic(container, Mapper[User, Order], UserOrderMapper)

    mapper = resolve_generic(container, Mapper[User, Order])
    assert isinstance(mapper, UserOrderMapper)


def test_generic_with_dependencies():
    """测试泛型服务有依赖的情况."""

    class Database:
        """数据库."""

    class GenericRepository(Generic[T]):
        """需要数据库依赖的仓储."""

        def __init__(self, db: Database) -> None:
            self.db = db

    class UserRepositoryWithDb(GenericRepository[User]):
        """用户仓储 (需要数据库)."""

        def __init__(self, db: Database) -> None:
            super().__init__(db)

    container = Container()
    container.register(Database, lifetime=Lifetime.SINGLETON)

    # 注册泛型服务，使用实现类而不是工厂函数
    # Container 会自动注入依赖
    register_generic(
        container,
        GenericRepository[User],
        UserRepositoryWithDb,
        lifetime=Lifetime.TRANSIENT,
    )

    repo = resolve_generic(container, GenericRepository[User])
    assert isinstance(repo, UserRepositoryWithDb)
    assert isinstance(repo.db, Database)


def test_generic_key_as_service_key():
    """测试 GenericKey 可以直接用作服务键."""
    container = Container()

    key = GenericKey(Repository, (User,))
    container.register(UserRepository, key=key, lifetime=Lifetime.SINGLETON)

    repo = container.resolve(key)
    assert isinstance(repo, UserRepository)
