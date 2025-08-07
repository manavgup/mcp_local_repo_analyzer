# =============================================================================
# README.md - Project Documentation
# =============================================================================
# Local Git Changes Analyzer

A FastMCP server for analyzing outstanding local git changes that haven't made their way to GitHub yet.

## Features

- **Working Directory Analysis**: Detect uncommitted changes
- **Staging Area Analysis**: Analyze staged changes ready for commit
- **Unpushed Commits**: Find commits that haven't been pushed to remote
- **Stash Analysis**: Examine stashed changes
- **Risk Assessment**: Identify high-risk changes and potential conflicts
- **Push Readiness**: Assess if repository is ready for remote push

## Installation

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)
- Git

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd local-git-analyzer

# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# For development dependencies
poetry install --with dev
```

## Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

## Usage

Run the FastMCP server:

```bash
# Using Poetry
poetry run python main.py

# Or activate the virtual environment
poetry shell
python main.py
```

Or use the CLI:

```bash
poetry run local-git-analyzer
```

## Development

### Setup Development Environment

```bash
# Install all dependencies including dev
poetry install --with dev,test

# Install pre-commit hooks
poetry run pre-commit install

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=local_git_analyzer --cov-report=html

# Run type checking
poetry run mypy local_git_analyzer

# Format code
poetry run black local_git_analyzer
poetry run isort local_git_analyzer

# Or use ruff for linting and formatting
poetry run ruff check local_git_analyzer
poetry run ruff format local_git_analyzer
```

### Poetry Commands

```bash
# Add a new dependency
poetry add <package>

# Add a development dependency
poetry add --group dev <package>

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree

# Build the package
poetry build

# Publish to PyPI
poetry publish
```

### Project Structure

```
local_git_analyzer/
├── main.py              # FastMCP server entry point
├── config.py            # Configuration and settings
├── models/              # Pydantic data models
├── services/            # Business logic services
├── tools/               # FastMCP tools
├── tests/               # Test files
├── pyproject.toml       # Poetry configuration
└── README.md            # This file
```

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=local_git_analyzer

# Run specific test file
poetry run pytest tests/test_git_client.py

# Run tests with specific markers
poetry run pytest -m unit
poetry run pytest -m integration
```

## License

MIT License
