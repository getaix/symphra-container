# Symphra Container - 使用 uv 的快速启动指南

## 🚀 5 分钟快速启动

### 前提条件
- Python 3.11+ 已安装
- uv 已安装（[安装 uv](https://docs.astral.sh/uv/getting-started/installation/)）

### 步骤 1: 进入项目目录
```bash
cd /opt/data/www/yfb/packages/symphra-container
```

### 步骤 2: 创建虚拟环境并安装依赖（一行命令）
```bash
uv sync --extra dev --extra frameworks
```

### 步骤 3: 激活虚拟环境
```bash
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows
```

### 步骤 4: 验证安装
```bash
python --version           # 应该是 3.11+
uv run pytest tests/ -v    # 运行测试验证
```

**完成！** ✅ 现在可以开始开发了。

---

## 🔧 常用命令速查表

### 开发工作流
```bash
# 激活虚拟环境（每次使用前）
source .venv/bin/activate

# 一次性运行所有检查
make check

# 或分别运行
make format  # 代码格式化
make lint    # 代码检查
make type    # 类型检查
make test    # 运行测试

# 生成覆盖率报告
make coverage
```

### 依赖管理
```bash
# 同步依赖
uv sync

# 安装额外依赖
uv sync --extra dev --extra frameworks

# 添加新包
uv pip install package-name

# 列出已安装的包
uv pip list
```

### 代码质量
```bash
# 格式化代码
uv run ruff format src/ tests/

# 检查代码问题
uv run ruff check src/ tests/

# 自动修复问题
uv run ruff check src/ tests/ --fix

# 类型检查
uv run mypy src/symphra_container --strict

# 运行测试
uv run pytest tests/ -v --cov
```

---

## 📊 项目统计

| 项目 | 详情 |
|-----|------|
| **Python 版本** | 3.11+ |
| **包管理器** | uv（超快速） |
| **代码检查** | ruff（50+ 规则集） |
| **类型检查** | mypy（严格模式） |
| **测试框架** | pytest（目标 90%+ 覆盖） |
| **测试覆盖** | >= 90% |
| **CI/CD** | GitHub Actions |

---

## ✅ 代码质量标准

在提交前，确保：
- ✅ `make format` 无错误（代码格式化）
- ✅ `make lint` 无警告（代码检查）
- ✅ `make type` 无错误（类型检查）
- ✅ `make test` 通过（测试通过，覆盖率 >= 90%）

**一行命令检查所有项**:
```bash
make check
```

---

## 🐛 troubleshooting

### Q: 找不到 uv 命令？
```bash
# 重新安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或
brew install uv
```

### Q: 虚拟环境未激活？
```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Q: Python 版本不对？
```bash
python --version  # 应该是 3.11+
uv python install 3.11  # 下载 Python 3.11
```

### Q: 依赖冲突？
```bash
uv sync  # 重新同步所有依赖
```

---

## 📚 查看更多

- **完整开发指南**: 查看 `DEVELOPMENT_SETUP.md`
- **项目规划**: 查看 `INTEGRATED_ROADMAP.md`
- **API 参考**: 查看 `API_DESIGN.md`
- **所有文档**: 查看 `INDEX.md`

---

**现在就开始吧！** 🎉

```bash
uv sync --extra dev --extra frameworks
source .venv/bin/activate
make check
```
