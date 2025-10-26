.PHONY: help install sync check format lint type test coverage clean all pre-commit update-deps

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Default target
help:
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Symphra Container - Development Tasks$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)Setup & Installation:$(NC)"
	@echo "  $(YELLOW)make install$(NC)       - Install dependencies with uv (dev + frameworks)"
	@echo "  $(YELLOW)make sync$(NC)          - Sync dependencies using uv.lock"
	@echo "  $(YELLOW)make update-deps$(NC)   - Update dependencies to latest versions"
	@echo ""
	@echo "$(GREEN)Quality Checks:$(NC)"
	@echo "  $(YELLOW)make check$(NC)         - Run all checks (format + lint + type + test)"
	@echo "  $(YELLOW)make format$(NC)        - Format code with ruff"
	@echo "  $(YELLOW)make lint$(NC)          - Check code style with ruff"
	@echo "  $(YELLOW)make type$(NC)          - Run type checking with mypy"
	@echo "  $(YELLOW)make test$(NC)          - Run unit tests"
	@echo "  $(YELLOW)make coverage$(NC)      - Run tests with coverage report"
	@echo ""
	@echo "$(GREEN)Pre-commit Checks:$(NC)"
	@echo "  $(YELLOW)make pre-commit$(NC)    - Run pre-commit checks (before git commit)"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  $(YELLOW)make clean$(NC)         - Remove build artifacts and cache"
	@echo "  $(YELLOW)make all$(NC)           - Full setup: clean + install + check"
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"

# ============ Installation & Setup ============

install:
	@echo "$(GREEN)→ Installing dependencies with uv...$(NC)"
	uv sync --extra dev --extra frameworks
	@echo "$(GREEN)✅ Installation complete$(NC)"

sync:
	@echo "$(GREEN)→ Syncing dependencies from uv.lock...$(NC)"
	uv sync
	@echo "$(GREEN)✅ Sync complete$(NC)"

update-deps:
	@echo "$(GREEN)→ Updating dependencies to latest versions...$(NC)"
	uv pip install --upgrade pip setuptools wheel
	uv sync --upgrade
	@echo "$(GREEN)✅ Dependencies updated$(NC)"

# ============ Code Quality Checks ============

check: format lint type test
	@echo "$(GREEN)╭─────────────────────────────────────────╮$(NC)"
	@echo "$(GREEN)│  ✅ All checks passed!                 │$(NC)"
	@echo "$(GREEN)╰─────────────────────────────────────────╯$(NC)"

format:
	@echo "$(GREEN)→ Formatting code with ruff...$(NC)"
	uv run ruff format src/ tests/
	@echo "$(GREEN)✅ Code formatted$(NC)"

lint:
	@echo "$(GREEN)→ Linting code with ruff...$(NC)"
	uv run ruff check src/ tests/ --fix
	@echo "$(GREEN)✅ Linting passed$(NC)"

type:
	@echo "$(GREEN)→ Type checking with mypy...$(NC)"
	uv run mypy src/symphra_container --strict
	@echo "$(GREEN)✅ Type checking passed$(NC)"

test:
	@echo "$(GREEN)→ Running tests with pytest...$(NC)"
	uv run pytest tests/ -v --tb=short
	@echo "$(GREEN)✅ Tests passed$(NC)"

coverage:
	@echo "$(GREEN)→ Running tests with coverage report...$(NC)"
	uv run pytest tests/ -v --cov=src/symphra_container --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✅ Coverage report generated at: htmlcov/index.html$(NC)"

# ============ Pre-commit Checks ============

pre-commit: format lint type
	@echo "$(GREEN)✅ Pre-commit checks passed. Ready to commit!$(NC)"

# ============ Maintenance ============

clean:
	@echo "$(GREEN)→ Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ coverage.xml .ruff_cache/ 2>/dev/null || true
	@echo "$(GREEN)✅ Cleaned$(NC)"

all: clean install check
	@echo "$(GREEN)╭─────────────────────────────────────────╮$(NC)"
	@echo "$(GREEN)│  ✅ Full setup complete!               │$(NC)"
	@echo "$(GREEN)╰─────────────────────────────────────────╯$(NC)"

# ============ Development Workflows ============

.PHONY: dev watch watch-tests

dev: install
	@echo "$(BLUE)Development environment ready!$(NC)"
	@echo "$(BLUE)Run 'make check' before committing code.$(NC)"

# Watch for changes and run tests (requires watchmedo from watchdog)
watch:
	@echo "$(GREEN)→ Watching for file changes...$(NC)"
	uv run pytest-watch tests/ -v --clear

# Run only tests (quick feedback)
watch-tests:
	@echo "$(GREEN)→ Running tests in watch mode...$(NC)"
	uv run pytest tests/ -v --tb=short -x  # -x stops at first failure

# ============ Useful Info ============

.PHONY: info versions

info:
	@echo "$(BLUE)Project Information:$(NC)"
	@echo "  Python version: $$(python --version)"
	@echo "  uv version: $$(uv --version)"
	@echo "  Virtual env: $${VIRTUAL_ENV}"
	@echo ""
	@echo "$(BLUE)Installed tools:$(NC)"
	@uv run ruff --version
	@uv run mypy --version
	@uv run pytest --version

versions:
	@echo "$(BLUE)Checking dependency versions...$(NC)"
	uv pip list | grep -E "ruff|mypy|pytest|black"
