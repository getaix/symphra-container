#!/usr/bin/env python3
"""演示泛型支持和可视化工具的功能."""

from typing import Generic, TypeVar

from symphra_container import Container, Lifetime
from symphra_container.generics import is_generic_type, register_generic, resolve_generic
from symphra_container.visualization import (
    debug_resolution,
    diagnose_container,
    print_dependency_graph,
    visualize_container,
)

T = TypeVar("T")


# ==================== 泛型支持演示 ====================


class Repository(Generic[T]):
    """通用仓储接口."""

    def get(self, entity_id: int) -> T:
        """获取实体."""
        raise NotImplementedError

    def save(self, entity: T) -> None:
        """保存实体."""
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

    def get(self, entity_id: int) -> User:
        return User(f"User {entity_id}")

    def save(self, entity: User) -> None:
        print(f"Saving user: {entity.name}")


class OrderRepository(Repository[Order]):
    """订单仓储实现."""

    def get(self, entity_id: int) -> Order:
        return Order(f"ORD-{entity_id}")

    def save(self, entity: Order) -> None:
        print(f"Saving order: {entity.order_id}")


def demo_generic_support() -> None:
    """演示泛型类型参数区分."""
    print("=" * 70)
    print("泛型类型参数区分演示")
    print("=" * 70)

    container = Container()

    # 注册不同类型参数的泛型服务
    print("\n1. 注册泛型服务")
    print("-" * 70)
    register_generic(container, Repository[User], UserRepository, lifetime=Lifetime.SINGLETON)
    register_generic(container, Repository[Order], OrderRepository, lifetime=Lifetime.SINGLETON)
    print("✅ 已注册 Repository[User] -> UserRepository")
    print("✅ 已注册 Repository[Order] -> OrderRepository")

    # 验证类型检查
    print("\n2. 泛型类型检查")
    print("-" * 70)
    print(f"Repository[User] 是泛型类型: {is_generic_type(Repository[User])}")
    print(f"Repository[Order] 是泛型类型: {is_generic_type(Repository[Order])}")
    print(f"User 是泛型类型: {is_generic_type(User)}")

    # 解析服务
    print("\n3. 解析泛型服务")
    print("-" * 70)
    user_repo = resolve_generic(container, Repository[User])
    order_repo = resolve_generic(container, Repository[Order])

    print(f"user_repo 类型: {type(user_repo).__name__}")
    print(f"order_repo 类型: {type(order_repo).__name__}")

    # 使用服务
    print("\n4. 使用泛型服务")
    print("-" * 70)
    user = user_repo.get(1)
    order = order_repo.get(123)

    print(f"获取用户: {user.name}")
    print(f"获取订单: {order.order_id}")

    user_repo.save(User("Alice"))
    order_repo.save(Order("ORD-999"))

    print()


# ==================== 可视化工具演示 ====================


class Logger:
    """日志服务."""

    def log(self, message: str) -> None:
        print(f"[LOG] {message}")


class Database:
    """数据库服务."""

    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def connect(self) -> None:
        self.logger.log("Database connected")


class UserService:
    """用户服务."""

    def __init__(self, repo: Repository[User], db: Database, logger: Logger) -> None:
        self.repo = repo
        self.db = db
        self.logger = logger


def demo_visualization() -> None:
    """演示可视化和调试工具."""
    print("=" * 70)
    print("可视化和调试工具演示")
    print("=" * 70)

    container = Container()

    # 设置依赖关系
    container.register(Logger, lifetime=Lifetime.SINGLETON)
    container.register(Database, lifetime=Lifetime.SINGLETON)
    register_generic(container, Repository[User], UserRepository, lifetime=Lifetime.SCOPED)
    container.register(UserService, lifetime=Lifetime.TRANSIENT)

    # 1. 生成依赖关系图 (DOT 格式)
    print("\n1. 依赖关系图 (DOT 格式)")
    print("-" * 70)
    dot = visualize_container(container, format="dot")
    print(dot)

    # 2. 生成依赖关系图 (Mermaid 格式)
    print("\n2. 依赖关系图 (Mermaid 格式)")
    print("-" * 70)
    mermaid = visualize_container(container, format="mermaid")
    print(mermaid)

    # 3. 打印依赖树
    print("\n3. 依赖关系树")
    print("-" * 70)
    print_dependency_graph(container)

    # 4. 调试特定服务的解析
    print("\n4. 调试 UserService 解析过程")
    print("-" * 70)
    debug_resolution(container, UserService)

    # 5. 容器健康诊断
    print("\n5. 容器健康诊断")
    print("-" * 70)
    report = diagnose_container(container)
    print(f"总服务数: {report.total_services}")
    print(f"单例服务: {report.singleton_count}")
    print(f"瞬态服务: {report.transient_count}")
    print(f"作用域服务: {report.scoped_count}")
    print(f"健康评分: {report.health_score:.1f}/100")

    if report.circular_dependencies:
        print("\n⚠️  发现循环依赖:")
        for dep1, dep2 in report.circular_dependencies:
            print(f"  - {dep1} <-> {dep2}")

    if report.unresolvable_services:
        print("\n⚠️  无法解析的服务:")
        for service in report.unresolvable_services:
            print(f"  - {service}")

    if report.warnings:
        print("\n⚠️  警告:")
        for warning in report.warnings:
            print(f"  - {warning}")

    if report.health_score == 100.0:
        print("\n✅ 容器完全健康!")

    print()


def main() -> None:
    """主函数."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Symphra Container 高级特性演示" + " " * 15 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # 演示泛型支持
    demo_generic_support()

    print("\n")

    # 演示可视化工具
    demo_visualization()

    print("=" * 70)
    print("演示完成!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
