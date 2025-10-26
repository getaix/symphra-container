# Flask Integration

## Install
```bash
pip install symphra-container[flask]
```

## Minimal Example
```python
from flask import Flask
from symphra_container import Container, Lifetime

app = Flask(__name__)
container = Container()

class Repo:
    def get(self, uid: int) -> dict: return {"id": uid}

container.register(Repo, lifetime=Lifetime.SINGLETON)

@app.route("/users/<int:uid>")
def get_user(uid: int):
    repo = container.resolve(Repo)
    return repo.get(uid)
```
