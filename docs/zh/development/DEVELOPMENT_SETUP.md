# Symphra Container - 开发环境设置指南

## 🚀 使用 uv 快速启动（推荐）

### 什么是 uv？

[uv](https://github.com/astral-sh/uv) 是一个超快速的 Python 包管理器和 resolver，用 Rust 编写。它比 pip、pip-tools 和 poetry 快 10-100 倍。

**优势**:
- ✅ 极快的安装速度（Rust 实现）
- ✅ 确定性的依赖解析
- ✅ 内置的 Python 版本管理
- ✅ 完全兼容 pip 和 PyPI
- ✅ 简单直观的命令行界面

### 安装 uv

#### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows (PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 使用包管理器
```bash
# Homebrew (macOS)
brew install uv

# Debian/Ubuntu
curl -LsSf https://astral.sh/uv/install.sh | sh

# Arch Linux
pacman -S uv
```

#### 验证安装
```bash
uv --version  # 应该显示 uv 0.x.x
uv python --version  # 应该显示 Python 3.11+
```

---

## 📦 项目初始化

### 方式 1: 使用 uv 从零开始（推荐）

```bash
# Step 1: 进入项目目录
cd /opt/data/www/yfb/packages/symphra-container

# Step 2: 初始化 uv 虚拟环境
uv venv .venv

# Step 3: 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows

# Step 4: 同步依赖（安装 dev 和 frameworks）
uv sync --extra dev --extra frameworks

# Step 5: 验证安装
python --version         # 应该是 3.11+
uv pip list             # 显示已安装的包
```

### 方式 2: 使用现有的虚拟环境

```bash
# Step 1: 创建虚拟环境
python3.11 -m venv .venv

# Step 2: 激活虚拟环境
source .venv/bin/activate

# Step 3: 使用 uv 安装依赖
uv pip install -e ".[dev,frameworks]"

# 或同步 pyproject.toml
uv sync --extra dev --extra frameworks
```

---

## 🔧 常用 uv 命令

### 依赖管理

```bash
# 同步依赖（推荐，会更新 uv.lock）
uv sync

# 同步特定额外依赖
uv sync --extra dev --extra frameworks

# 安装单个包
uv pip install package-name

# 卸载包
uv pip uninstall package-name

# 列出已安装的包
uv pip list

# 查看依赖树
uv pip tree

# 导出 requirements.txt
uv pip freeze > requirements.txt
uv pip compile pyproject.toml -o requirements.txt
```

### 虚拟环境管理

```bash
# 创建虚拟环境
uv venv .venv

# 创建指定 Python 版本的虚拟环境
uv venv .venv --python 3.12

# 删除虚拟环境
rm -rf .venv  # macOS/Linux
rmdir /s .venv  # Windows

# 查看所有可用的 Python 版本
uv python list

# 下载特定 Python 版本
uv python install 3.12
```

### 工作流命令

```bash
# 一次性运行命令（自动创建临时虚拟环境）
uv run ruff check src/
uv run pytest tests/

# 指定 Python 版本运行
uv run --python 3.12 pytest tests/
```

---

## 🧪 代码质量检查工作流

### 自动格式化和检查

```bash
# 1. 运行所有检查和测试（推荐）
uv run make check  # 需要有 Makefile

# 或分别运行：

# 2. Ruff 代码检查和自动修复
uv run ruff check src/ tests/ --fix

# 3. Ruff 代码格式化
uv run ruff format src/ tests/

# 4. MyPy 类型检查
uv run mypy src/symphra_container --strict

# 5. 运行测试和覆盖率
uv run pytest tests/ -v --cov

# 6. 生成覆盖率 HTML 报告
uv run pytest tests/ --cov --cov-report=html
# 打开 htmlcov/index.html 查看详细报告
```

### 按优先级检查

**P0 - 必须通过**:
```bash
uv run ruff check src/ tests/        # Lint 检查
uv run ruff format src/ tests/       # 格式检查
uv run mypy src/ --strict            # 类型检查
```

**P1 - 强烈建议**:
```bash
uv run pytest tests/ --cov=90        # 测试和覆盖率
```

**P2 - 可选但推荐**:
```bash
uv run ruff check src/ --select RUF  # Ruff 特定规则
```

---

## 📋 Makefile 便捷命令（可选）

创建 `Makefile` 简化命令：

```makefile
.PHONY: help install check test format lint type clean

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies with uv"
	@echo "  make sync        - Sync dependencies with uv.lock"
	@echo "  make check       - Run all checks (lint, format, type, test)"
	@echo "  make format      - Format code with ruff"
	@echo "  make lint        - Lint code with ruff"
	@echo "  make type        - Check types with mypy"
	@echo "  make test        - Run tests with pytest"
	@echo "  make coverage    - Run tests with coverage report"
	@echo "  make clean       - Remove build artifacts"

install:
	uv sync --extra dev --extra frameworks

sync:
	uv sync

check: format lint type test

format:
	uv run ruff format src/ tests/
	@echo "✅ Code formatted"

lint:
	uv run ruff check src/ tests/ --fix
	@echo "✅ Linting passed"

type:
	uv run mypy src/symphra_container --strict
	@echo "✅ Type checking passed"

test:
	uv run pytest tests/ -v
	@echo "✅ Tests passed"

coverage:
	uv run pytest tests/ -v --cov --cov-report=html
	@echo "✅ Coverage report generated: htmlcov/index.html"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/
	@echo "✅ Cleaned"
```

使用：
```bash
make check       # 运行所有检查
make format      # 代码格式化
make test        # 运行测试
make coverage    # 生成覆盖率报告
make clean       # 清理临时文件
```

---

## 🎯 开发流程

### 1. 开始工作

```bash
# 激活虚拟环境
source .venv/bin/activate

# 同步最新依赖
uv sync
```

### 2. 编写代码

```bash
# 编写您的代码
# src/symphra_container/container.py
```

### 3. 格式化和检查

```bash
# 自动格式化
uv run ruff format src/ tests/

# 运行 lint 检查并自动修复
uv run ruff check src/ tests/ --fix

# 运行类型检查
uv run mypy src/symphra_container --strict

# 如果有问题，修复后再检查
```

### 4. 运行测试

```bash
# 快速运行
uv run pytest tests/unit/ -v

# 完整测试和覆盖率
uv run pytest tests/ -v --cov

# 生成 HTML 报告
uv run pytest tests/ --cov --cov-report=html
```

### 5. 提交代码

```bash
# 确保所有检查都通过
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run mypy src/ --strict
uv run pytest tests/ --cov=90

# 提交
git add .
git commit -m "feat: add new feature"
```

---

## 📊 代码质量检查详解

### Ruff 检查规则

**启用的主要规则集**:

| 代码 | 名称 | 说明 |
|-----|------|------|
| F | Pyflakes | 查找可能的错误 |
| E/W | pycodestyle | 代码风格问题 |
| C90 | mccabe | 复杂度检查 |
| I | isort | 导入排序 |
| N | pep8-naming | 命名规范 |
| D | pydocstyle | 文档字符串 |
| UP | pyupgrade | Python 语法升级 |
| ANN | flake8-annotations | 类型注解检查 |
| B | flake8-bugbear | 常见错误 |
| S | flake8-bandit | 安全问题 |
| RUF | Ruff specific | Ruff 特定规则 |

**禁用的规则** (太严格):
- `ANN101`: 忽略 `self` 的类型注解
- `S101`: 忽略 assert
- `D100/D104`: 忽略文件级文档字符串

**运行检查**:
```bash
# 查看所有问题（不修复）
uv run ruff check src/

# 自动修复可以修复的问题
uv run ruff check src/ --fix

# 只显示特定规则的问题
uv run ruff check src/ --select E,W

# 显示详细信息
uv run ruff check src/ --show-fixes
```

### MyPy 类型检查

**严格模式设置** (`--strict`):
- 要求所有函数都有类型注解
- 禁止隐式 `Any` 类型
- 禁止未检查的转换
- 等等

**运行检查**:
```bash
# 严格模式检查
uv run mypy src/symphra_container --strict

# 忽略特定问题
uv run mypy src/ --ignore-missing-imports

# 生成报告
uv run mypy src/ --html htmlmypy/
```

### Pytest 覆盖率

**目标**: >= 90% 覆盖率

**运行测试**:
```bash
# 简单运行
uv run pytest tests/

# 显示覆盖率摘要
uv run pytest tests/ --cov

# 显示缺失的行
uv run pytest tests/ --cov --cov-report=term-missing

# 生成 HTML 报告
uv run pytest tests/ --cov --cov-report=html
# 打开 htmlcov/index.html

# 强制覆盖率最低值
uv run pytest tests/ --cov=symphra_container --cov-fail-under=90
```

---

## 📝 提交前检查清单

在提交代码前，确保：

```bash
# 1. 格式化检查
uv run ruff format src/ tests/
# 检查是否有改动，如有则修复并确认

# 2. Lint 检查
uv run ruff check src/ tests/ --fix
# 应该输出：✅ All checks passed

# 3. 类型检查
uv run mypy src/symphra_container --strict
# 应该没有错误

# 4. 测试
uv run pytest tests/ --cov=90 -v
# 应该所有测试通过，覆盖率 >= 90%

# 5. 验证 Python 版本
python --version
# 应该是 3.11 或更高

# 全部完成后提交
git add .
git commit -m "your message"
```

---

## 🐛 常见问题

### Q: uv 命令找不到？
A: 确保已安装 uv 并在 PATH 中。运行 `uv --version` 验证。

### Q: 虚拟环境没激活？
A: 运行 `source .venv/bin/activate` (macOS/Linux) 或 `.venv\Scripts\activate` (Windows)

### Q: 依赖冲突？
A: 运行 `uv sync` 重新同步依赖，这会读取 `uv.lock` 文件。

### Q: 想添加新的依赖？
A: 编辑 `pyproject.toml` 后运行 `uv sync`，或直接 `uv pip install package-name`。

### Q: Ruff 报错太多？
A: 首先运行 `uv run ruff check --fix` 自动修复，然后手动修复剩余问题。

### Q: MyPy 严格模式太严格？
A: 这是一个特性，不是 bug。严格类型检查会让代码更安全。如果必须放宽，编辑 `pyproject.toml` 的 `[tool.mypy]` 部分。

### Q: 测试覆盖率不足 90%？
A: 添加更多单元测试。使用 `pytest --cov --cov-report=html` 查看未覆盖的代码。

---

## 🔗 更多资源

- [uv 官方文档](https://docs.astral.sh/uv/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [MyPy 文档](https://mypy.readthedocs.io/)
- [Pytest 文档](https://docs.pytest.org/)

---

## 🎓 开发最佳实践

### 1. 始终保持代码质量

```bash
# 在提交前运行这个一体化命令
uv run ruff format src/ tests/ && \
uv run ruff check src/ tests/ --fix && \
uv run mypy src/ --strict && \
uv run pytest tests/ --cov=90
```

### 2. 编写可测试的代码

- 依赖注入，方便 mock
- 小的、专注的函数
- 明确的错误处理
- 完整的类型注解

### 3. 持续集成

这些检查应该在 CI/CD 流程中自动运行：

```yaml
# .github/workflows/ci.yml
- name: Format check
  run: uv run ruff format --check src/ tests/

- name: Lint check
  run: uv run ruff check src/ tests/

- name: Type check
  run: uv run mypy src/ --strict

- name: Tests
  run: uv run pytest tests/ --cov=90
```

### 4. 性能优化

- 使用 uv 替代 pip（快 10-100 倍）
- 定期更新依赖
- 移除未使用的导入和依赖
- 使用 `--no-cache` 强制重新安装（如有问题）

---

**现在您已经准备好开发了！** 🚀

下一步：
1. 运行 `uv sync --extra dev --extra frameworks`
2. 运行 `uv run pytest tests/` 验证设置
3. 按照 INTEGRATED_ROADMAP.md 开始开发
