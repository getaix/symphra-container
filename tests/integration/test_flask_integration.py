"""Flask 集成测试.

这些测试只在安装了 Flask 时运行。
"""

from __future__ import annotations

import pytest

# 尝试导入 Flask
try:
    from flask import Flask

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# 如果没有安装 Flask, 跳过所有测试
pytestmark = pytest.mark.skipif(
    not FLASK_AVAILABLE,
    reason="Flask not installed. Install with: pip install symphra-container[flask]",
)

if FLASK_AVAILABLE:
    from symphra_container import Container, Lifetime
    from symphra_container.integrations.flask import FlaskContainer


@pytest.fixture
def container() -> Container:
    """创建测试容器."""
    return Container()


@pytest.fixture
def app(container: Container) -> Flask:
    """创建测试 Flask 应用."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def flask_container(app: Flask, container: Container) -> FlaskContainer:
    """创建 Flask 容器."""
    return FlaskContainer(app, container)


class UserService:
    """测试服务: 用户管理."""

    def get_user(self, user_id: int) -> dict:
        """获取用户信息."""
        return {"id": user_id, "name": f"User {user_id}"}

    def get_all_users(self) -> list[dict]:
        """获取所有用户."""
        return [{"id": 1, "name": "User 1"}, {"id": 2, "name": "User 2"}]


class EmailService:
    """测试服务: 邮件发送."""

    def __init__(self, user_service: UserService) -> None:
        """初始化邮件服务."""
        self.user_service = user_service
        self.sent_emails: list[tuple[str, str]] = []

    def send(self, to: str, subject: str) -> bool:
        """发送邮件."""
        self.sent_emails.append((to, subject))
        return True


def test_flask_container_initialization(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试 Flask 容器初始化."""
    assert flask_container.app is app
    assert flask_container.container is container


def test_resolve_singleton_service(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试解析单例服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)

    # 解析服务
    with app.test_request_context():
        service1 = flask_container.resolve(UserService)
        service2 = flask_container.resolve(UserService)

        assert service1 is service2  # 单例应该是同一实例


def test_resolve_transient_service(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试解析瞬时服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.TRANSIENT)

    # 解析服务
    with app.test_request_context():
        service1 = flask_container.resolve(UserService)
        service2 = flask_container.resolve(UserService)

        assert service1 is not service2  # 瞬时应该是不同实例


def test_resolve_scoped_service(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试解析作用域服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SCOPED)

    # 在第一个请求上下文中
    with app.test_request_context():
        service1 = flask_container.resolve(UserService)
        service2 = flask_container.resolve(UserService)
        assert service1 is service2  # 同一请求中应该是同一实例

    # 在第二个请求上下文中
    with app.test_request_context():
        service3 = flask_container.resolve(UserService)
        assert service3 is not service1  # 不同请求应该是不同实例


def test_inject_decorator_basic(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试 @inject 装饰器基本功能."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)

    # 创建视图
    @app.route("/users/<int:user_id>")
    @flask_container.inject
    def get_user(user_id: int, user_service: UserService):
        return user_service.get_user(user_id)

    # 测试请求
    with app.test_client() as client:
        response = client.get("/users/123")
        assert response.status_code == 200
        assert response.json == {"id": 123, "name": "User 123"}


def test_inject_decorator_with_dependencies(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试 @inject 装饰器处理带依赖的服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)
    container.register(EmailService, lifetime=Lifetime.TRANSIENT)

    # 创建视图
    @app.route("/notify/<int:user_id>")
    @flask_container.inject
    def notify_user(user_id: int, email_service: EmailService):
        user = email_service.user_service.get_user(user_id)
        email_service.send(f"user{user_id}@example.com", "Notification")
        return {"user": user, "emails_sent": len(email_service.sent_emails)}

    # 测试请求
    with app.test_client() as client:
        response = client.get("/notify/456")
        assert response.status_code == 200
        data = response.json
        assert data["user"] == {"id": 456, "name": "User 456"}
        assert data["emails_sent"] == 1


def test_inject_decorator_multiple_services(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试 @inject 装饰器注入多个服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)
    container.register(EmailService, lifetime=Lifetime.TRANSIENT)

    # 创建视图
    @app.route("/process/<int:user_id>")
    @flask_container.inject
    def process(user_id: int, user_service: UserService, email_service: EmailService):
        user = user_service.get_user(user_id)
        email_service.send(f"user{user_id}@example.com", "Processing")
        return {"user": user, "emails": len(email_service.sent_emails)}

    # 测试请求
    with app.test_client() as client:
        response = client.get("/process/789")
        assert response.status_code == 200
        data = response.json
        assert data["user"] == {"id": 789, "name": "User 789"}
        assert data["emails"] == 1


def test_inject_decorator_skips_provided_args(
    app: Flask, container: Container, flask_container: FlaskContainer
) -> None:
    """测试 @inject 装饰器跳过已提供的参数."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)

    # 创建视图(user_id 由路由提供)
    @app.route("/users/<int:user_id>")
    @flask_container.inject
    def get_user(user_id: int, user_service: UserService):
        # user_id 不应该被注入，应该来自路由
        return user_service.get_user(user_id)

    # 测试请求
    with app.test_client() as client:
        response = client.get("/users/999")
        assert response.status_code == 200
        assert response.json == {"id": 999, "name": "User 999"}


def test_request_scope_cleanup(app: Flask, container: Container, flask_container: FlaskContainer) -> None:
    """测试请求作用域清理."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SCOPED)

    # 记录服务实例
    instances = []

    @app.route("/test")
    @flask_container.inject
    def test_view(user_service: UserService):
        instances.append(id(user_service))
        return {"ok": True}

    # 发送多个请求
    with app.test_client() as client:
        client.get("/test")
        client.get("/test")
        client.get("/test")

    # 每个请求应该有不同的实例
    assert len(set(instances)) == 3
