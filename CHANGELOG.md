# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-08-07

### Added
- Initial release of MCP Local Repository Analyzer
- MCP server for analyzing outstanding git changes in repositories
- Working directory analysis for uncommitted changes with risk assessment
- Staging area analysis for staged changes ready for commit
- Unpushed commits detection and analysis
- Comprehensive summary analysis across repository state
- Multiple transport support (stdio, HTTP, WebSocket, SSE)
- CLI interface with multiple configuration options
- Bundled mcp_shared_lib for seamless installation
- Self-contained package requiring no external dependencies
- Services for change detection, diff analysis, and status tracking
- Integration with GitPython for repository operations
- Comprehensive test suite with unit and integration tests
- Production-ready PyPI package configuration
