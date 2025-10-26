# 安装指南

Symphra 容器支持纯 Python 环境，并提供可选的框架集成。

## 安装核心库
```bash
pip install symphra-container
```

## 可选框架集成
按需安装对应的可选依赖：
```bash
# FastAPI 集成
pip install symphra-container[fastapi]

# Flask 集成
pip install symphra-container[flask]

# Django 集成
pip install symphra-container[django]

# 安装所有集成
pip install symphra-container[all]
```

## Python 版本要求
- Python 3.10+（推荐 3.11/3.12）

## 依赖说明
- 核心库无强制第三方依赖
- 集成模块根据框架自动导入，未安装时具备友好错误提示（见 `symphra_container.integrations.__init__`）

## 验证安装
```python
import symphra_container
print(symphra_container.__version__)
```
