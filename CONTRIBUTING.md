# Contributing to MCP Local Repository Analyzer

Thank you for your interest in contributing to MCP Local Repository Analyzer! This guide outlines the development workflow and standards for this project.

## Development Environment Setup

### Prerequisites
- Python 3.10 or higher
- Poetry for dependency management
- Git for version control
- Pre-commit for code quality checks

### Initial Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/manavgup/mcp_local_repo_analyzer.git
   cd mcp_local_repo_analyzer
   ```

2. **Install dependencies:**
   ```bash
   poetry install --with test,dev
   ```

3. **Install pre-commit hooks:**
   ```bash
   poetry run pre-commit install
   ```

4. **Verify installation:**
   ```bash
   poetry run pytest tests/ -v
   ```

## Code Standards

### Code Style
This project uses automated code formatting and linting:

- **Black**: Code formatting with 88-character line length
- **Ruff**: Fast Python linter for code quality
- **mypy**: Static type checking
- **pre-commit**: Automated checks before commits

### Running Code Quality Checks
```bash
# Run all pre-commit checks
poetry run pre-commit run --all-files

# Individual tools
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/
```

### Type Annotations
- All functions must include type annotations for parameters and return values
- Use modern union syntax (`X | Y` instead of `Union[X, Y]`)
- Import types from `typing` when needed

### Documentation Standards
- All public functions and classes must have docstrings
- Use Google-style docstrings
- Include type information in docstrings where helpful
- Update README.md for significant feature changes

## Testing Requirements

### Test Structure
- Tests are located in the `tests/` directory
- Use pytest for all testing
- Organize tests to mirror the `src/` directory structure
- Use descriptive test function names

### Test Types
- **Unit tests**: Fast, isolated tests (marked with `@pytest.mark.unit`)
- **Integration tests**: Cross-component tests (marked with `@pytest.mark.integration`)
- **Slow tests**: Tests taking >5 seconds (marked with `@pytest.mark.slow`)

### Running Tests
```bash
# Run all tests
poetry run pytest tests/

# Run specific test types
poetry run pytest -m "unit and not slow"
poetry run pytest -m integration

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```

### Test Coverage
- Maintain minimum 80% test coverage
- All new features must include comprehensive tests
- Bug fixes must include regression tests

## Development Workflow

### Branch Strategy
1. Create feature branches from `main`: `git checkout -b feature/your-feature-name`
2. Make commits with descriptive messages
3. Push branch and create pull request
4. Address review feedback
5. Merge after approval

### Commit Message Format
```
type(scope): short description

Longer description if needed explaining the changes
and their rationale.

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

### Pull Request Process
1. **Before creating PR:**
   - Ensure all tests pass locally
   - Run pre-commit checks
   - Update documentation if needed
   - Add changelog entry if applicable

2. **PR Requirements:**
   - Clear title and description
   - Link to related issues
   - Include testing instructions
   - Request appropriate reviewers

3. **Review Process:**
   - Address all reviewer feedback
   - Ensure CI checks pass
   - Squash commits if requested
   - Await approval before merging

## Project-Specific Guidelines

### MCP Local Repository Analyzer Architecture
This service analyzes outstanding git changes in repositories:

- **MCP Tools**: Working directory, staging area, unpushed commits, and summary analysis
- **Services**: ChangeDetector, DiffAnalyzer, StatusTracker for comprehensive git analysis
- **Entry Points**: CLI with multiple transport support, FastMCP server
- **Default Port**: 9070 (HTTP mode)

### Key Components
- **ChangeDetector**: Identifies uncommitted changes with risk assessment
- **DiffAnalyzer**: Analyzes code differences and impact
- **StatusTracker**: Monitors repository status across multiple repos
- **Transport Layer**: Supports stdio, HTTP, WebSocket, SSE protocols

### Running the Service
```bash
# Development mode (stdio)
poetry run python -m mcp_local_repo_analyzer.main --transport stdio

# HTTP server mode
poetry run python -m mcp_local_repo_analyzer.main --transport http --port 9070

# Using make commands from workspace root
make serve-analyzer
```

### Available MCP Tools
- `analyze_working_directory`: Analyze uncommitted changes with risk assessment
- `analyze_staged_changes`: Analyze staged changes ready for commit
- `get_outstanding_summary`: Comprehensive change summary across repositories
- `compare_with_remote`: Compare local branch with remote branch

### Testing Git Operations
- Tests use temporary Git repositories
- Factory patterns generate realistic test scenarios
- Mock external dependencies (GitHub API, etc.)
- Use `@pytest.mark.git` for tests requiring Git setup

## Issue Reporting

### Bug Reports
When reporting bugs, please include:
- Python version and operating system
- Complete error messages and stack traces
- Git repository state (if relevant)
- Minimal code example to reproduce the issue
- Expected vs. actual behavior

### Feature Requests
For new features, please provide:
- Clear use case and motivation
- Detailed description of proposed functionality
- Consider impact on existing git analysis workflows
- Suggest implementation approach if possible

## Getting Help

- **Documentation**: Check the README.md and inline documentation
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Code Review**: Don't hesitate to ask for clarification during reviews

## Recognition

Contributors are recognized in:
- Git commit history
- Release notes for significant contributions
- Contributors section in README.md

Thank you for contributing to MCP Local Repository Analyzer!
