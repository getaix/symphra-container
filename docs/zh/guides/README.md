# Symphra Container

企业级 Python 依赖注入容器库，支持同步和异步服务。

## 特性

- 🎯 4 种生命周期支持 (Singleton, Transient, Scoped, Factory)
- 💪 完整的类型提示支持
- ⚡ 高性能实现
- 🔄 循环依赖检测与解决
- 🎪 拦截器系统
- 🌍 统一异步/同步支持
- 🔌 可选的框架集成 (FastAPI, Flask, Django)

## 安装

```bash
# 基础安装
pip install symphra-container

# 安装 FastAPI 集成
pip install symphra-container[fastapi]

# 安装 Flask 集成
pip install symphra-container[flask]

# 安装 Django 集成
pip install symphra-container[django]

# 安装所有集成
pip install symphra-container[all]
```

## 快速开始

### 基本用法

```python
from symphra_container import Container, Lifetime

# 创建容器
container = Container()

# 注册服务
class UserService:
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "User"}

container.register(UserService, lifetime=Lifetime.SINGLETON)

# 解析服务
service = container.resolve(UserService)
user = service.get_user(123)
```

### 异步服务

```python
import asyncio

class AsyncUserService:
    async def get_user(self, user_id: int):
        await asyncio.sleep(0.1)
        return {"id": user_id, "name": "Async User"}

# 注册异步服务(自动检测)
container.register(AsyncUserService, lifetime=Lifetime.SINGLETON)

# 使用 resolve_async 解析
async def main():
    service = await container.resolve_async(AsyncUserService)
    user = await service.get_user(456)
    print(user)

asyncio.run(main())
```

### 框架集成 (可选)

#### FastAPI

```python
from fastapi import FastAPI, Depends
from symphra_container.integrations import fastapi_inject, setup_fastapi

app = FastAPI()
setup_fastapi(app, container)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: UserService = Depends(fastapi_inject(UserService))
):
    return await user_service.get_user(user_id)
```

#### Flask

```python
from flask import Flask
from symphra_container.integrations import FlaskContainer

app = Flask(__name__)
flask_container = FlaskContainer(app, container)

@app.route("/users/<int:user_id>")
@flask_container.inject
def get_user(user_id: int, user_service: UserService):
    return user_service.get_user(user_id)
```

#### Django

```python
# settings.py
from symphra_container.integrations import DjangoContainer

CONTAINER = Container()
DjangoContainer.setup(CONTAINER)

MIDDLEWARE = [
    'symphra_container.integrations.django.ContainerMiddleware',
    # ...
]

# views.py
@DjangoContainer.inject
def user_view(request, user_id: int, user_service: UserService):
    return JsonResponse(user_service.get_user(user_id))
```

## 文档

- [快速入门指南](./QUICK_START_UV.md)
- [API 文档](./API_DESIGN.md)
- [框架集成指南](./docs/FRAMEWORK_INTEGRATIONS.md)
- [测试指南](./docs/zh/testing-guide.md)

## 性能

- 服务解析: ~0.05ms
- 单例缓存: ~0.01ms
- 内存占用: < 1MB (1000 服务)

## 许可

MIT
