# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install dependencies (ALWAYS use uv, never pip)
uv sync --frozen --all-extras --dev

# Run all pre-commit hooks (ruff + mypy)
pre-commit run --all-files

# Run test suite
uv run pytest

# Run specific test file
uv run pytest tests/unit/jira/test_issues.py -v

# Run tests with coverage
uv run pytest --cov=src/mcp_atlassian --cov-report=term-missing

# Lint and format
uv run ruff check src/ --fix
uv run ruff format src/

# Run the MCP server
uv run mcp-atlassian
uv run mcp-atlassian --oauth-setup   # OAuth wizard
uv run mcp-atlassian -v              # Verbose mode
```

## Architecture

This is an MCP (Model Context Protocol) server for Atlassian Jira and Confluence. Supports Cloud and Server/Data Center deployments.

### Key Directories

- `src/mcp_atlassian/jira/` - Jira client and operations
- `src/mcp_atlassian/confluence/` - Confluence client and operations
- `src/mcp_atlassian/servers/` - FastMCP server implementations and tool registration
- `src/mcp_atlassian/models/` - Pydantic data models for API responses
- `src/mcp_atlassian/preprocessing/` - HTML→Markdown content transformation
- `src/mcp_atlassian/utils/` - Shared utilities (auth, logging, SSL)

### Mixin-Based Composition Pattern

`JiraFetcher` and `ConfluenceFetcher` use **mixin composition** rather than inheritance:

```python
# src/mcp_atlassian/jira/__init__.py
class JiraFetcher(ProjectsMixin, FieldsMixin, IssuesMixin, SearchMixin, ...):
    """Combines all Jira operations via mixins"""
```

Each mixin (in separate files like `issues.py`, `search.py`, `projects.py`) handles a single responsibility. The `*Fetcher` classes compose these mixins together.

### Server & Tool Registration

- Entry point: `src/mcp_atlassian/__init__.py` → `servers/main.py`
- Tools registered via `@jira_mcp.tool()` and `@confluence_mcp.tool()` decorators in `servers/jira.py` and `servers/confluence.py`
- Dependency injection in `servers/dependencies.py` provides fetchers to tools
- Tool naming convention: `{service}_{action}` (e.g., `jira_create_issue`, `confluence_get_page`)

### Data Flow

```
CLI Entry → FastMCP Server Setup → Load Config from Env → Register Tools
    ↓
Tool Execution → Dependency Injection → Fetcher Mixins → API Calls
    ↓
Response Models (Pydantic) → Preprocessing (HTML→Markdown) → Return
```

### Authentication (auto-detected in order)

1. OAuth 2.0 (3LO) - `ATLASSIAN_OAUTH_CLIENT_ID` + `SECRET`
2. Bring-Your-Own Token - `ATLASSIAN_OAUTH_ACCESS_TOKEN` + `CLOUD_ID`
3. Personal Access Token - `JIRA_PERSONAL_TOKEN` / `CONFLUENCE_PERSONAL_TOKEN`
4. Basic Auth (API Token) - `USERNAME` + `API_TOKEN`

## Code Conventions

- **Python**: ≥3.10, <3.14
- **Line length**: 88 characters
- **Type hints**: Required on all functions
- **Docstrings**: Google-style
- **Imports**: Absolute, sorted by ruff
- **Models**: Extend `ApiModel` base class with `from_api_response()` and `to_simplified_dict()`

## Git Workflow

```bash
# Always create feature branches
git checkout -b feature/description   # New feature
git checkout -b fix/issue-description # Bug fix

# Use trailers for attribution
git commit --trailer "Reported-by:<name>"
git commit --trailer "Github-Issue:#<number>"
```

Never work directly on `main`. Tests and lint must pass before committing.
