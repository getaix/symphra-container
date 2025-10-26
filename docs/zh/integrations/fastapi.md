# FastAPI 集成

## 安装
```bash
pip install symphra-container[fastapi]
```

## 使用示例
```python
from symphra_container import Container, Lifetime
from symphra_container.integrations import fastapi_inject, setup_fastapi
from fastapi import FastAPI, Depends

class UserService:
    async def get_user(self, user_id: int):
        return {"id": user_id, "name": "Alice"}

container = Container()
container.register(UserService, lifetime=Lifetime.SCOPED)

app = FastAPI()
setup_fastapi(app, container)

@app.get("/users/{user_id}")
async def get_user(user_id: int, svc: UserService = Depends(fastapi_inject(UserService))):
    return await svc.get_user(user_id)
```
