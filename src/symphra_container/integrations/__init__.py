"""框架集成模块.

⚠️ 可选功能: 所有框架集成都是可选的。
只安装你需要的框架依赖，例如:
  - pip install symphra-container[fastapi]
  - pip install symphra-container[flask]
  - pip install symphra-container[django]
  - pip install symphra-container[all]  # 安装所有集成

如果导入失败，会给出友好的错误提示。
"""

from __future__ import annotations

__all__: list[str] = []

# 尝试导入各个框架集成（如果已安装）
try:
    from .fastapi import inject as fastapi_inject
    from .fastapi import setup_container as setup_fastapi

    __all__.extend(["fastapi_inject", "setup_fastapi"])
except ImportError:
    pass

try:
    from .flask import FlaskContainer

    __all__.append("FlaskContainer")
except ImportError:
    pass

try:
    from .django import DjangoContainer

    __all__.append("DjangoContainer")
except ImportError:
    pass
