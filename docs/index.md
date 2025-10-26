# Symphra 容器

企业级 Python 依赖注入容器。提供高性能、强类型、异步支持与可扩展的拦截器与作用域管理。

- 4 种生命周期：`Singleton`、`Transient`、`Scoped`、`Factory`
- 混合服务键：类型与字符串键均可
- 完整类型提示与泛型支持
- 同步/异步统一解析
- 拦截器与性能指标
- 循环依赖检测与诊断工具

## 快速体验
```python
from symphra_container import Container, Lifetime

class UserRepo:
    def get(self, uid: int) -> dict:
        return {"id": uid, "name": "Alice"}

class UserService:
    def __init__(self, repo: UserRepo):
        self.repo = repo
    async def get_user(self, uid: int):
        return self.repo.get(uid)

container = Container()
container.register(UserRepo, lifetime=Lifetime.SINGLETON)
container.register(UserService, lifetime=Lifetime.SCOPED)

# 解析服务（支持同步/异步）
service = container.resolve(UserService)
```

## 文档导航
- 中文文档：见左侧「中文文档」分组
- English docs: see the "English Documentation" group

## 功能概览
- 服务注册与解析，自动依赖注入
- 泛型服务键（如 `Repository[User]` 与 `Repository[Order]` 区分）
- 作用域管理与资源释放
- 错误处理与诊断（依赖可视化、调试输出）

## 版本记录
请参见「变更日志」。历史版本以 Git 提交为准。