"""FastAPI 集成测试.

这些测试只在安装了 FastAPI 时运行。
"""

from __future__ import annotations

import pytest

# 尝试导入 FastAPI
try:
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# 如果没有安装 FastAPI, 跳过所有测试
pytestmark = pytest.mark.skipif(
    not FASTAPI_AVAILABLE,
    reason="FastAPI not installed. Install with: pip install symphra-container[fastapi]",
)

if FASTAPI_AVAILABLE:
    from symphra_container import Container, Lifetime
    from symphra_container.integrations.fastapi import (
        get_container,
        inject,
        setup_container,
    )
    from symphra_container.exceptions import ServiceNotFoundError


@pytest.fixture
def container() -> Container:
    """创建测试容器."""
    return Container()


@pytest.fixture
def app(container: Container) -> FastAPI:
    """创建测试 FastAPI 应用."""
    app = FastAPI()
    setup_container(app, container)
    return app


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


def test_setup_container(app: FastAPI, container: Container) -> None:
    """测试容器设置."""
    # 验证容器已设置
    assert get_container() is container


def test_inject_singleton_service(app: FastAPI, container: Container) -> None:
    """测试注入单例服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)

    # 创建路由
    @app.get("/users/{user_id}")
    def get_user(user_id: int, user_service: UserService = Depends(inject(UserService))):
        return user_service.get_user(user_id)

    # 测试请求
    client = TestClient(app)
    response = client.get("/users/123")

    assert response.status_code == 200
    assert response.json() == {"id": 123, "name": "User 123"}


def test_inject_transient_service(app: FastAPI, container: Container) -> None:
    """测试注入瞬时服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.TRANSIENT)

    # 创建路由
    @app.get("/users")
    def get_users(user_service: UserService = Depends(inject(UserService))):
        return user_service.get_all_users()

    # 测试请求
    client = TestClient(app)
    response = client.get("/users")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_inject_with_dependencies(app: FastAPI, container: Container) -> None:
    """测试注入带依赖的服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)
    container.register(EmailService, lifetime=Lifetime.TRANSIENT)

    # 创建路由
    @app.post("/emails")
    def send_email(email_service: EmailService = Depends(inject(EmailService))):
        email_service.send("test@example.com", "Test Subject")
        return {"sent": len(email_service.sent_emails)}

    # 测试请求
    client = TestClient(app)
    response = client.post("/emails")

    assert response.status_code == 200
    assert response.json() == {"sent": 1}


def test_inject_scoped_service(app: FastAPI, container: Container) -> None:
    """测试注入作用域服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SCOPED)

    # 创建路由
    @app.get("/users/{user_id}")
    def get_user(user_id: int, user_service: UserService = Depends(inject(UserService))):
        return user_service.get_user(user_id)

    # 测试请求
    client = TestClient(app)
    response = client.get("/users/456")

    assert response.status_code == 200
    assert response.json() == {"id": 456, "name": "User 456"}


def test_inject_multiple_services(app: FastAPI, container: Container) -> None:
    """测试注入多个服务."""
    # 注册服务
    container.register(UserService, lifetime=Lifetime.SINGLETON)
    container.register(EmailService, lifetime=Lifetime.TRANSIENT)

    # 创建路由
    @app.get("/notify/{user_id}")
    def notify_user(
        user_id: int,
        user_service: UserService = Depends(inject(UserService)),
        email_service: EmailService = Depends(inject(EmailService)),
    ):
        user = user_service.get_user(user_id)
        email_service.send(f"user{user_id}@example.com", "Notification")
        return {"user": user, "emails_sent": len(email_service.sent_emails)}

    # 测试请求
    client = TestClient(app)
    response = client.get("/notify/789")

    assert response.status_code == 200
    data = response.json()
    assert data["user"] == {"id": 789, "name": "User 789"}
    assert data["emails_sent"] == 1


def test_container_not_initialized_error() -> None:
    """测试容器未初始化时的错误."""
    # 重置全局容器
    from symphra_container.integrations import fastapi as fastapi_module

    fastapi_module._container = None

    # 应该抛出异常
    with pytest.raises(RuntimeError, match="Container not initialized"):
        get_container()


def test_service_not_registered_error(app: FastAPI, container: Container) -> None:
    """测试服务未注册时的错误."""

    class UnregisteredService:
        pass

    # 创建路由(服务未注册)
    @app.get("/unregistered")
    def get_unregistered(
        service: UnregisteredService = Depends(inject(UnregisteredService)),
    ):
        return {"ok": True}

    # 测试请求应该失败
    client = TestClient(app)
    with pytest.raises(ServiceNotFoundError):
        client.get("/unregistered")
