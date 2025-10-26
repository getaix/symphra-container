# Testing Guide

## Overview

Symphra Container follows these testing standards:

- Unit test coverage: >= 90%
- Integration tests: cover framework integrations
- Performance tests: benchmarks for critical operations
- Tooling: pytest + pytest-asyncio + pytest-cov

---

## Test Layout

```
tests/
├── unit/                  # Unit tests
│   ├── test_container.py  # Container basics
│   ├── test_lifetimes.py  # Lifetime management
│   ├── test_injection.py  # Dependency injection
│   ├── test_decorators.py # Decorators
│   └── ...
├── integration/           # Integration tests
│   ├── test_fastapi.py    # FastAPI
│   ├── test_flask.py      # Flask
│   └── ...
├── performance/           # Performance tests
│   ├── test_resolution_speed.py
│   └── ...
└── conftest.py            # Shared fixtures and config
```

## Quick Start

- Run unit tests: `uv run pytest -q tests/unit`
- Full test suite with coverage: `uv run pytest -q --cov=symphra_container --cov-report=xml`
- Specific test file: `uv run pytest tests/unit/test_container.py -q`

## Examples

### Container basics

```python
import pytest
from symphra_container import Container, Lifetime

class Service:
    pass

def test_lifetime_singleton():
    container = Container()
    container.register(Service, lifetime=Lifetime.SINGLETON)
    s1 = container.resolve(Service)
    s2 = container.resolve(Service)
    assert s1 is s2
```

### Async factory

```python
import pytest
from symphra_container import Container

@pytest.mark.asyncio
async def test_async_factory():
    container = Container()

    async def create_service():
        return "async_service"

    container.register_async_factory("service", create_service)
    result = await container.resolve_async("service")
    assert result == "async_service"
```

## Integration (FastAPI)

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from symphra_container import Container, Injected
from symphra_container.integrations.fastapi import DIMiddleware

app = FastAPI()
container = Container()

class UserService:
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Test User"}

container.register(UserService)
app.add_middleware(DIMiddleware, container=container)

@app.get("/users/{user_id}")
def get_user(user_id: int, service: "UserService" = Injected):
    return service.get_user(user_id)

client = TestClient(app)
resp = client.get("/users/1")
assert resp.status_code == 200
assert resp.json()["id"] == 1
```
