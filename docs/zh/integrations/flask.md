# Flask 集成

## 安装
```bash
pip install symphra-container[flask]
```

## 使用示例
```python
from symphra_container import Container, Lifetime
from symphra_container.integrations import FlaskContainer
from flask import Flask

class EmailService:
    def send(self, to: str, text: str):
        print("send", to, text)

container = Container()
container.register(EmailService, lifetime=Lifetime.SCOPED)

app = Flask(__name__)
flask_container = FlaskContainer(app, container)

@app.route("/send/<email>")
@flask_container.inject
def send(email: str, email_service: EmailService):
    email_service.send(email, "Hello")
    return {"status": "ok"}
```
