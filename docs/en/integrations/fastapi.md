# FastAPI Integration

## Install
```bash
pip install symphra-container[fastapi]
```

## Minimal Example
```python
from fastapi import FastAPI, Depends
from symphra_container import Container, Lifetime

app = FastAPI()
container = Container()

class Repo:
    def get(self, uid: int) -> dict: return {"id": uid}

container.register(Repo, lifetime=Lifetime.SINGLETON)

# Integration helper (pseudo)
from symphra_container.integrations.fastapi import inject

@app.get("/users/{uid}")
def get_user(uid: int, repo: Repo = Depends(inject(Repo))):
    return repo.get(uid)
```
