# Getting Started

This guide helps you get productive with Symphra Container in minutes.

## 1. Create the container and register services
```python
from symphra_container import Container, Lifetime

class EmailService:
    def send(self, to: str, text: str):
        print(f"send to {to}: {text}")

class UserService:
    def __init__(self, email: EmailService):
        self.email = email
    def onboard(self, user_email: str):
        self.email.send(user_email, "Welcome!")

container = Container()
container.register(EmailService, lifetime=Lifetime.SINGLETON)
container.register(UserService, lifetime=Lifetime.TRANSIENT)
```

## 2. Resolve services (automatic DI)
```python
service = container.resolve(UserService)
service.onboard("alice@example.com")
```

## 3. Use scopes (e.g., per web request)
```python
with container.create_scope() as scope:
    scoped_service = scope.resolve(UserService)
    scoped_service.onboard("bob@example.com")
```

## 4. Async support
```python
import asyncio

class AsyncRepo:
    async def get(self, uid: int) -> dict:
        return {"id": uid}

class AsyncService:
    def __init__(self, repo: AsyncRepo):
        self.repo = repo
    async def fetch(self, uid: int):
        return await self.repo.get(uid)

container.register(AsyncRepo, lifetime=Lifetime.SINGLETON)
container.register(AsyncService, lifetime=Lifetime.SCOPED)

async def main():
    s = container.resolve(AsyncService)
    print(await s.fetch(1))

asyncio.run(main())
```

## 5. Generic service keys
```python
from typing import Generic, TypeVar
from symphra_container.generics import register_generic

T = TypeVar("T")

class Repository(Generic[T]):
    def get(self, id: int) -> T: ...

class User: ...
class UserRepository(Repository[User]):
    def get(self, id: int) -> User: return User()

register_generic(container, Repository[User], UserRepository)
user_repo = container.resolve(Repository[User])
```

## Next steps
- Read "Installation" and "Core Concepts"
- See "API Reference" for complete interfaces
