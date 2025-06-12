# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   🔍 LOCAL GIT ANALYZER - Makefile
#   (An MCP server for analyzing local Git repositories)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Description: Build & automation helpers for the Local Git Analyzer project
# Usage: run `make` or `make help` to view available targets
#
# help: 🔍 LOCAL GIT ANALYZER  (An MCP server for analyzing local Git repositories)
#
# ──────────────────────────────────────────────────────────────────────────
# Project variables
PROJECT_NAME      = local-git-analyzer
PACKAGE_NAME      = local_git_analyzer
DOCS_DIR          = docs
HANDSDOWN_PARAMS  = -o $(DOCS_DIR)/ -n $(PACKAGE_NAME) --name "Local Git Analyzer" --cleanup

TEST_DOCS_DIR ?= $(DOCS_DIR)/docs/test

# Project-wide clean-up targets
DIRS_TO_CLEAN := __pycache__ .pytest_cache .tox .ruff_cache .pyre .mypy_cache .pytype \
                 dist build site .eggs *.egg-info .cache htmlcov certs \
                 $(VENV_DIR).sbom $(COVERAGE_DIR) \
                 node_modules coverage_report test-reports cache

FILES_TO_CLEAN := .coverage coverage.xml profile.prof profile.pstats \
                  $(PROJECT_NAME).sbom.json \
                  snakefood.dot packages.dot classes.dot \
                  $(DOCS_DIR)/pstats.png \
                  $(DOCS_DIR)/docs/test/sbom.md \
                  $(DOCS_DIR)/docs/test/{unittest,full,index,test}.md \
				  $(DOCS_DIR)/docs/images/coverage.svg $(LICENSES_MD) $(METRICS_MD) \
				  *.log *.txt *.png *.pkl

COVERAGE_DIR ?= $(DOCS_DIR)/docs/coverage
LICENSES_MD  ?= $(DOCS_DIR)/docs/test/licenses.md
METRICS_MD   ?= $(DOCS_DIR)/docs/metrics/loc.md

# -----------------------------------------------------------------------------
# Container resource configuration
CONTAINER_MEMORY = 2048m
CONTAINER_CPUS   = 2

# Virtual-environment variables
VENVS_DIR := $(HOME)/.venv
VENV_DIR  := $(VENVS_DIR)/$(PROJECT_NAME)

# Poetry configuration
POETRY_VENV := $(shell poetry env info --path 2>/dev/null || echo "")

# =============================================================================
# 📖 DYNAMIC HELP
# =============================================================================
.PHONY: help
help:
	@grep "^# help\:" Makefile | grep -v grep | sed 's/\# help\: //' | sed 's/\# help\://'

# =============================================================================
# 🌱 VIRTUAL ENVIRONMENT & INSTALLATION
# =============================================================================
# help: 🌱 VIRTUAL ENVIRONMENT & INSTALLATION
# help: venv                 - Create a fresh virtual environment with Poetry
# help: activate             - Show how to activate the virtual environment
# help: install              - Install project dependencies with Poetry
# help: install-dev          - Install project (incl. dev deps) with Poetry
# help: update               - Update all installed deps with Poetry
# help: poetry-install       - Install Poetry if not present
.PHONY: venv activate install install-dev update poetry-install

poetry-install:
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "📦 Installing Poetry..."; \
		curl -sSL https://install.python-poetry.org | python3 -; \
		echo "✅ Poetry installed. You may need to restart your shell."; \
	else \
		echo "✅ Poetry is already installed."; \
	fi

venv: poetry-install
	@echo "🌱 Creating virtual environment with Poetry..."
	@poetry env remove --all 2>/dev/null || true
	@poetry install --no-dev
	@echo "✅ Virtual environment created with Poetry."
	@echo "💡 Activate with: poetry shell"

activate:
	@echo "💡 To activate the virtual environment, use one of:"
	@echo "    poetry shell"
	@echo "    source $$(poetry env info --path)/bin/activate"

install: poetry-install
	@echo "📦 Installing project dependencies..."
	@poetry install --no-dev

install-dev: poetry-install
	@echo "📦 Installing project with dev dependencies..."
	@poetry install

update: poetry-install
	@echo "⬆️ Updating dependencies..."
	@poetry update

# help: check-env            - Verify all required env vars are present
.PHONY: check-env
check-env:
	@echo "🔎 Checking environment variables..."
	@if [ -f ".env" ]; then \
		echo "✅ .env file found"; \
	else \
		echo "⚠️  No .env file found"; \
	fi

# =============================================================================
# ▶️ SERVE & TESTING
# =============================================================================
# help: ▶️ SERVE & TESTING
# help: serve                - Run MCP server with poetry
# help: serve-http           - Run HTTP server on port 8000
# help: dev                  - Run in development mode with auto-reload
# help: run                  - Execute the main application
# help: test                 - Run unit tests with pytest
# help: test-integration     - Run integration tests
# help: test-all             - Run all tests (unit + integration)
# help: test-manual          - Run manual tests
# help: test-quick           - Run quick tests only

.PHONY: serve serve-http dev run test test-integration test-all test-manual test-quick

serve:
	@echo "🚀 Starting MCP server..."
	poetry run python -m $(PACKAGE_NAME)

serve-http:
	@echo "🌐 Starting HTTP server on port 8000..."
	poetry run python -m $(PACKAGE_NAME).run_http_server

dev:
	@echo "🔄 Running in development mode..."
	poetry run python -m $(PACKAGE_NAME) --dev

run:
	@echo "▶️ Running application..."
	poetry run python -m $(PACKAGE_NAME)

test:
	@echo "🧪 Running unit tests..."
	poetry run pytest tests/unit/ -v --tb=short

test-integration:
	@echo "🧪 Running integration tests..."
	poetry run pytest tests/integration/ -v --tb=short

test-all:
	@echo "🧪 Running all tests..."
	poetry run pytest tests/ -v --tb=short

test-manual:
	@echo "🧪 Running manual tests..."
	poetry run pytest tests/test_manual.py -v --tb=short

test-quick:
	@echo "🧪 Running quick tests..."
	poetry run pytest tests/integration/test_quick.py -v --tb=short

# =============================================================================
# 🧹 CLEANUP
# =============================================================================
# help: 🧹 CLEANUP
# help: clean                - Remove caches, build artifacts, and temp files
# help: clean-all            - Deep clean including virtual environments

.PHONY: clean clean-all

clean:
	@echo "🧹 Cleaning workspace..."
	@# Remove matching directories
	@for dir in $(DIRS_TO_CLEAN); do \
		find . -type d -name "$$dir" -exec rm -rf {} + 2>/dev/null || true; \
	done
	@# Remove listed files
	@rm -f $(FILES_TO_CLEAN) 2>/dev/null || true
	@# Delete Python bytecode
	@find . -name '*.py[cod]' -delete 2>/dev/null || true
	@echo "✅ Clean complete."

clean-all: clean
	@echo "🧹 Deep cleaning including Poetry environment..."
	@poetry env remove --all 2>/dev/null || true
	@echo "✅ Deep clean complete."

# =============================================================================
# 📊 COVERAGE & METRICS
# =============================================================================
# help: 📊 COVERAGE & METRICS
# help: coverage             - Run tests with coverage reporting
# help: coverage-html        - Generate HTML coverage report
# help: coverage-report      - Show coverage report in terminal
# help: pip-licenses         - Generate dependency license inventory
# help: scc                  - Quick LoC/complexity snapshot with scc
# help: scc-report           - Generate detailed LoC metrics

.PHONY: coverage coverage-html coverage-report pip-licenses scc scc-report

coverage:
	@echo "📊 Running tests with coverage..."
	@mkdir -p $(TEST_DOCS_DIR)
	poetry run pytest --cov=$(PACKAGE_NAME) --cov-report=term --cov-report=xml --cov-report=html:$(COVERAGE_DIR) tests/
	@echo "✅ Coverage report generated."

coverage-html:
	@echo "📊 Generating HTML coverage report..."
	poetry run pytest --cov=$(PACKAGE_NAME) --cov-report=html:$(COVERAGE_DIR) tests/
	@echo "✅ HTML coverage report: $(COVERAGE_DIR)/index.html"

coverage-report:
	@echo "📊 Showing coverage report..."
	poetry run coverage report -m

pip-licenses:
	@echo "📜 Generating license inventory..."
	@mkdir -p $(dir $(LICENSES_MD))
	poetry run pip-licenses --format=markdown --with-authors --with-urls > $(LICENSES_MD)
	@echo "📜 License inventory written to $(LICENSES_MD)"

scc:
	@echo "📊 Code complexity analysis..."
	@if command -v scc >/dev/null 2>&1; then \
		scc --by-file -i py .; \
	else \
		echo "❌ scc not installed. Install with: go install github.com/boyter/scc/v3@latest"; \
	fi

scc-report:
	@echo "📊 Generating detailed LoC report..."
	@mkdir -p $(dir $(METRICS_MD))
	@if command -v scc >/dev/null 2>&1; then \
		printf "# Lines of Code Report\n\n" > $(METRICS_MD); \
		scc . --format=html-table >> $(METRICS_MD); \
		printf "\n\n## Per-file metrics\n\n" >> $(METRICS_MD); \
		scc -i py,yaml,toml,md --by-file . --format=html-table >> $(METRICS_MD); \
		echo "📊 LoC metrics captured in $(METRICS_MD)"; \
	else \
		echo "❌ scc not installed. Install with: go install github.com/boyter/scc/v3@latest"; \
	fi

# =============================================================================
# 🔍 LINTING & STATIC ANALYSIS
# =============================================================================
# help: 🔍 LINTING & STATIC ANALYSIS
# help: lint                 - Run the full linting suite
# help: black                - Format code with black
# help: isort                - Sort imports with isort
# help: flake8               - Run flake8 checks
# help: pylint               - Run pylint analysis
# help: mypy                 - Run mypy type checking
# help: bandit               - Security scan with bandit
# help: ruff                 - Run ruff linter and formatter
# help: pre-commit           - Run pre-commit hooks

# List of individual lint targets
LINTERS := black isort flake8 pylint mypy bandit ruff

.PHONY: lint $(LINTERS) pre-commit

lint:
	@echo "🔍 Running full lint suite (checks only)..."
	@set -e; for linter in $(LINTERS); do \
		if [ "$$linter" = "ruff" ]; then \
			echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
			echo "• $$linter (check only)"; \
			poetry run ruff check $(PACKAGE_NAME) tests/ || echo "⚠️ $$linter failed"; \
		else \
			echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
			echo "• $$linter"; \
			$(MAKE) $$linter || echo "⚠️ $$linter failed"; \
		fi \
	done

.PHONY: black isort flake8 pylint mypy bandit ruff pre-commit

black:
	@echo "🎨 Formatting with black..."
	poetry run black $(PACKAGE_NAME) tests/

isort:
	@echo "🔀 Sorting imports with isort..."
	poetry run isort $(PACKAGE_NAME) tests/

flake8:
	@echo "🐍 Running flake8..."
	poetry run flake8 $(PACKAGE_NAME) tests/

pylint:
	@echo "🐛 Running pylint..."
	poetry run pylint $(PACKAGE_NAME)

mypy:
	@echo "🏷️ Running mypy type checking..."
	poetry run mypy $(PACKAGE_NAME)

bandit:
	@echo "🛡️ Running bandit security scan..."
	poetry run bandit -r $(PACKAGE_NAME)

ruff:
	@echo "⚡ Running ruff..."
	poetry run ruff check $(PACKAGE_NAME) tests/
	poetry run ruff format $(PACKAGE_NAME) tests/

pre-commit:
	@echo "🪄 Running pre-commit hooks..."
	poetry run pre-commit run --all-files
