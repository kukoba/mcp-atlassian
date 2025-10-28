# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Atlassian is a Model Context Protocol (MCP) server that provides AI assistants with seamless integration to Atlassian products (Jira and Confluence). It supports both Cloud and Server/Data Center deployments.

**Key Technologies:**
- Python 3.10+ with `uv` for dependency management
- FastMCP framework for MCP server implementation
- `atlassian-python-api` for Atlassian API interactions
- Pydantic for data validation and models
- Docker for containerized deployment

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync
uv sync --frozen --all-extras --dev

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate.ps1  # Windows

# Set up pre-commit hooks
pre-commit install

# Configure environment variables
cp .env.example .env
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=mcp_atlassian

# Run specific test file
uv run pytest tests/unit/jira/test_issues.py

# Run specific test class or function
uv run pytest tests/unit/jira/test_issues.py::TestJiraIssues::test_create_issue
```

### Code Quality
```bash
# Run all pre-commit checks
pre-commit run --all-files

# Format code with ruff
ruff format .

# Lint with ruff
ruff check .

# Type check with pyright (preferred over mypy)
pyright
```

### Running the Server
```bash
# Run with stdio transport (default)
uv run mcp-atlassian

# Run with verbose logging
uv run mcp-atlassian -v      # INFO level
uv run mcp-atlassian -vv     # DEBUG level

# Run with HTTP transport (SSE)
uv run mcp-atlassian --transport sse --port 9000

# Run with streamable-http transport
uv run mcp-atlassian --transport streamable-http --port 9000

# Run OAuth setup wizard
uv run mcp-atlassian --oauth-setup -v

# Use MCP Inspector for testing
npx @modelcontextprotocol/inspector uv run mcp-atlassian
```

## Architecture

### High-Level Structure

The codebase is organized into distinct layers:

1. **MCP Server Layer** (`src/mcp_atlassian/servers/`)
   - `main.py`: Main AtlassianMCP server with tool filtering and lifecycle management
   - `jira.py`: Jira-specific FastMCP tools (prefixed with `jira_`)
   - `confluence.py`: Confluence-specific FastMCP tools (prefixed with `confluence_`)
   - `context.py`: MainAppContext dataclass holding configuration state
   - `dependencies.py`: Dependency injection for fetcher instances

2. **Client/Fetcher Layer** (`src/mcp_atlassian/jira/`, `src/mcp_atlassian/confluence/`)
   - `client.py`: Core API client with authentication handling
   - Feature modules: `issues.py`, `search.py`, `pages.py`, `comments.py`, etc.
   - `config.py`: Configuration dataclass with auth detection logic

3. **Data Models** (`src/mcp_atlassian/models/`)
   - Pydantic models for Jira/Confluence entities
   - `base.py`: Base model classes with common functionality
   - Separate subdirectories for `jira/` and `confluence/` models

4. **Preprocessing** (`src/mcp_atlassian/preprocessing/`)
   - Content transformation logic (HTML to Markdown, Markdown to Confluence Storage Format)

5. **Utilities** (`src/mcp_atlassian/utils/`)
   - `oauth.py`: OAuth token management with keyring storage
   - `environment.py`: Service availability detection
   - `logging.py`: Logging setup with masking for sensitive data
   - `tools.py`: Tool filtering utilities

### Authentication Flow

The server supports multiple authentication methods with auto-detection:

1. **Username + API Token** (Cloud): Basic auth with Atlassian API tokens
2. **Personal Access Token (PAT)**: For Server/Data Center deployments
3. **OAuth 2.0 Standard**: Full OAuth flow with token refresh
4. **OAuth BYOT** (Bring Your Own Token): User-provided tokens for multi-tenant scenarios

**Priority order in `config.py`:**
1. Username/API Token (if both present)
2. Personal Access Token (if URL is Server/DC and PAT is set)
3. OAuth BYOT (if `ATLASSIAN_OAUTH_CLOUD_ID` + `ATLASSIAN_OAUTH_ACCESS_TOKEN`)
4. OAuth Standard (if OAuth client credentials are configured)

### Multi-User Authentication

For HTTP transports (SSE, streamable-http), the `UserTokenMiddleware` extracts per-request authentication:
- **Cloud**: `Authorization: Bearer <oauth_token>` + optional `X-Atlassian-Cloud-Id`
- **Server/DC**: `Authorization: Token <pat>`

This enables multi-tenant deployments where each user provides their own credentials.

### Tool Registration and Filtering

Tools are registered using FastMCP decorators with tags:
```python
@jira_mcp.tool(tags={"jira", "read"})
async def get_issue(ctx: Context, issue_key: str) -> str:
    ...
```

The `AtlassianMCP` class overrides `_mcp_list_tools()` to filter based on:
- `enabled_tools`: Explicit tool whitelist (ENABLED_TOOLS env var)
- `read_only`: Exclude tools tagged with "write"
- Service availability: Exclude Jira/Confluence tools if not configured

### Configuration Pattern

Each service (Jira/Confluence) has a `Config` dataclass:
```python
@dataclass
class JiraConfig:
    url: str
    username: str | None = None
    api_token: str | None = None
    personal_token: str | None = None
    oauth_config: OAuthConfig | None = None
    # ... other fields

    @classmethod
    def from_env(cls) -> "JiraConfig":
        # Loads from environment variables

    def is_auth_configured(self) -> bool:
        # Checks if any auth method is available
```

Configs are loaded once at server startup in `main_lifespan()` and stored in `MainAppContext`.

### Dependency Injection

Tools use `get_jira_fetcher()` or `get_confluence_fetcher()` to obtain client instances:
```python
async def get_jira_fetcher(ctx: Context) -> JiraFetcher:
    # Extracts config from lifespan context
    # Checks for per-request user tokens (HTTP transport)
    # Returns configured JiraFetcher instance
```

This pattern allows:
- Server-level config fallback
- Per-request user authentication override
- Consistent error handling

## Testing Patterns

### Test Organization
- `tests/unit/`: Unit tests organized by module (jira/, confluence/, models/, servers/, utils/)
- `tests/integration/`: Integration tests for cross-cutting concerns
- `tests/fixtures/`: Mock data factories (jira_mocks.py, confluence_mocks.py)
- `tests/utils/`: Test utilities (assertions.py, factories.py, mocks.py, base.py)

### Common Testing Utilities
```python
from tests.utils.factories import create_jira_issue, create_confluence_page
from tests.utils.mocks import MockJiraClient, MockConfluenceClient
```

### Mocking Atlassian API
Tests use `unittest.mock` to mock `atlassian-python-api` clients:
```python
from unittest.mock import MagicMock, patch

@patch("mcp_atlassian.jira.client.Jira")
def test_get_issue(mock_jira_class):
    mock_jira_instance = MagicMock()
    mock_jira_class.return_value = mock_jira_instance
    # Set up mock responses
    mock_jira_instance.issue.return_value = {...}
```

## Important Patterns and Conventions

### Error Handling
- All tools return JSON-serialized responses (even errors)
- Use `MCPAtlassianAuthenticationError` for auth issues
- Mask sensitive data in logs with `mask_sensitive()` utility

### Type Annotations
- Use modern Python type syntax: `str | None` (not `Optional[str]`)
- Use `list[T]`, `dict[K, V]` (not `List[T]`, `Dict[K, V]`)
- Use `type[T]` for class types

### Docstrings
- Use Google-style docstrings for all public functions
- Include Args, Returns, and Raises sections

### Configuration Priority
Environment variables take precedence: CLI flags > environment variables > defaults

### Logging
- Use module-level loggers: `logger = logging.getLogger(__name__)`
- Always mask tokens/passwords: `mask_sensitive(token)`
- Use appropriate log levels: DEBUG for detailed info, INFO for lifecycle events, WARNING for fallbacks

### OAuth Token Storage
- Tokens stored in OS keyring (keyring library) or fallback to `~/.mcp-atlassian/tokens.json`
- Token refresh handled automatically in `oauth.py`

## Environment Variables Reference

See `.env.example` for comprehensive list. Key variables:

**Essential:**
- `JIRA_URL`, `CONFLUENCE_URL`: Instance URLs
- Auth: `JIRA_USERNAME`/`JIRA_API_TOKEN` or `JIRA_PERSONAL_TOKEN`
- OAuth: `ATLASSIAN_OAUTH_CLIENT_ID`, `ATLASSIAN_OAUTH_CLIENT_SECRET`, `ATLASSIAN_OAUTH_CLOUD_ID`

**Optional:**
- `READ_ONLY_MODE=true`: Disable write operations
- `ENABLED_TOOLS`: Comma-separated tool names
- `MCP_VERBOSE=true`, `MCP_VERY_VERBOSE=true`: Logging levels
- `CONFLUENCE_SPACES_FILTER`, `JIRA_PROJECTS_FILTER`: Content filtering
- Proxy: `HTTP_PROXY`, `HTTPS_PROXY`, `SOCKS_PROXY`
- Custom headers: `JIRA_CUSTOM_HEADERS`, `CONFLUENCE_CUSTOM_HEADERS`

## Docker Usage

The project is distributed as a Docker image:
```bash
# Pull image
docker pull ghcr.io/sooperset/mcp-atlassian:latest

# Run with env file
docker run --rm -i --env-file .env ghcr.io/sooperset/mcp-atlassian:latest

# Run OAuth setup
docker run --rm -i -p 8080:8080 \
  -v "${HOME}/.mcp-atlassian:/home/app/.mcp-atlassian" \
  ghcr.io/sooperset/mcp-atlassian:latest --oauth-setup -v
```

## Code Style Requirements

- **Line length**: 88 characters (ruff/black default)
- **Formatter**: ruff (replaces black)
- **Linter**: ruff (replaces flake8, isort)
- **Type checker**: pyright (preferred over mypy)
- Pre-commit hooks enforce all checks automatically

## Key Implementation Details

### Content Transformation
- **Confluence → Markdown**: `markdownify` library (preprocessing/confluence.py)
- **Markdown → Confluence Storage Format**: `markdown-to-confluence` library

### API Version Detection
- Confluence API v2 detection via `v2_adapter.py`
- Fallback to v1 API for older Server/DC versions

### Jira Field Handling
- Default fields defined in `jira/constants.py`: `DEFAULT_READ_JIRA_FIELDS`
- Custom field detection with `jira_search_fields` tool
- Support for `*all` to retrieve all fields including custom ones

### Multi-Cloud OAuth
Enable minimal OAuth mode for multi-tenant scenarios:
```bash
docker run -e ATLASSIAN_OAUTH_ENABLE=true -p 9000:9000 \
  ghcr.io/sooperset/mcp-atlassian:latest \
  --transport streamable-http --port 9000
```
Each request includes `Authorization: Bearer <token>` and `X-Atlassian-Cloud-Id` headers.

## Debugging

### Enable Debug Logging
```bash
# Via CLI
uv run mcp-atlassian -vv

# Via environment
MCP_VERY_VERBOSE=true uv run mcp-atlassian

# Log to stdout instead of stderr
MCP_LOGGING_STDOUT=true uv run mcp-atlassian
```

### View Claude Desktop Logs
```bash
# macOS
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log

# Windows
type %APPDATA%\Claude\logs\mcp*.log | more
```

### Common Issues
- **Authentication failures**: Check token validity, verify Server/DC vs Cloud URL format
- **SSL errors**: Set `JIRA_SSL_VERIFY=false` or `CONFLUENCE_SSL_VERIFY=false` for self-signed certs
- **OAuth issues**: Ensure `offline_access` scope is included for token refresh
- **Custom headers not working**: Enable `MCP_VERY_VERBOSE=true` to see parsed headers

## Release Process

Follows semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

Version automatically determined by `uv-dynamic-versioning` from git tags.
