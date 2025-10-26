# Django 集成

## 安装
```bash
pip install symphra-container[django]
```

## 使用示例
在 `settings.py` 中配置：
```python
from symphra_container import Container, Lifetime
from symphra_container.integrations import DjangoContainer

CONTAINER = Container()
CONTAINER.register(SomeService, lifetime=Lifetime.SCOPED)
```

在视图中使用：
```python
from symphra_container.integrations import DjangoContainer

def user_view(request, user_id):
    svc = DjangoContainer.resolve(SomeService)
    return JsonResponse(svc.get(user_id))

@DjangoContainer.inject
def email_view(request, email_service: EmailService):
    email_service.send("test@example.com", "Hello")
    return JsonResponse({"status": "sent"})
```
