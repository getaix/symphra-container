# Django Integration

## Install
```bash
pip install symphra-container[django]
```

## Settings
```python
# settings.py
from symphra_container import Container, Lifetime

CONTAINER = Container()

class Repo:
    def get(self, uid: int) -> dict: return {"id": uid}

CONTAINER.register(Repo, lifetime=Lifetime.SINGLETON)
```

## Usage in views
```python
# views.py
from django.http import JsonResponse
from django.conf import settings

def get_user(request, uid: int):
    repo = settings.CONTAINER.resolve(Repo)
    return JsonResponse(repo.get(uid))
```
