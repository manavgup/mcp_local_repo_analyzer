# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- MCP server for analyzing outstanding git changes in repositories
- Working directory analysis for uncommitted changes
- Staging area analysis for staged changes ready for commit
- Unpushed commits detection and analysis
- Risk assessment for changes and potential conflicts
- Comprehensive summary analysis across repository state
- Multiple transport support (stdio, HTTP, WebSocket, SSE)
- CLI interface with multiple configuration options
- Integration with mcp_shared_lib for common functionality

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - 2025-08-07

### Added
- Initial release of MCP Local Repository Analyzer
- FastMCP server for analyzing outstanding local git changes
- MCP tools for working directory, staging area, and unpushed commits analysis
- Services for change detection, diff analysis, and status tracking
- CLI with transport configuration options
- Integration with GitPython for repository operations
- Comprehensive test suite with unit and integration tests
- Documentation and setup instructions
