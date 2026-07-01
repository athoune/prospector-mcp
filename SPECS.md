# Prospector MCP Server — Technical Specification

## 1. Overview

An MCP (Model Context Protocol) server that exposes [Prospector](https://github.com/landscapeio/prospector) — the Python static analysis tool — through its **native Python API**, providing callable tools for any MCP-compatible agent (OpenCode, Claude Desktop, Cursor, etc.).

The server invokes Prospector's Python API directly on demand and returns structured results. It is distributed as a self-contained Python package runnable via `uvx`.

## 2. Goals & Non-Goals

### Goals
- Run Prospector against a single file or an entire directory.
- Return machine-readable, structured output (messages with severity, location, code).
- Support both `stdio` and `SSE` transports via FastMCP.
- Be installable and runnable with zero configuration via `uvx`.
- Provide sensible defaults so that most users never need a config file.
- Support layered configuration: built-in defaults → global config → project config.
- Enforce safe defaults: respect `.gitignore`, skip `.env`/`.venv` files, enforce execution timeouts.

### Non-Goals
- Real-time file watching or daemon mode.
- Rewriting or autofixing code.
- GUI or web dashboard.
- Managing Prospector plugins beyond what Prospector itself supports.

## 3. Architecture

### 3.1 Stack
- **Framework**: [FastMCP](https://github.com/jlowin/fastmcp) (decorator-based, minimal boilerplate).
- **Transports**: `stdio` (default for local agents) and `SSE` (optional for remote/HTTP).
- **Python**: 3.11+ (to leverage `tomllib` and modern typing).
- **Distribution**: PyPI package, runnable via `uvx run prospector-mcp`.
- **Process model**: Stateless. Each tool invocation calls Prospector's Python API (`prospector.run.Prospector`) directly in the same process. Execution runs inside `asyncio.to_thread` with a timeout.

### 3.2 Prospector Python API

Prospector exposes a programmatic API centered on two classes:

- `prospector.config.ProspectorConfig` — holds all configuration (paths, profile, strictness, ignores, tools).
- `prospector.run.Prospector` — executes the analysis.

Typical usage:
```python
from prospector.config import ProspectorConfig
from prospector.run import Prospector

config = ProspectorConfig(workdir=Path("/project"))
# Note: ProspectorConfig reads CLI args via setoptconf by default;
# for programmatic use we will need to inject values into the
# configuration manager before instantiation.
prospector = Prospector(config)
prospector.execute()
messages = prospector.get_messages()   # list[Message]
summary = prospector.get_summary()     # dict[str, Any]
```

A `Message` object contains:
- `source` — tool name (e.g., `"pylint"`)
- `code` — rule code (e.g., `"C0301"`)
- `location` — `Location` with `path`, `line`, `character`
- `message` — human-readable text

The server maps these objects directly to JSON-friendly dicts; no CLI or JSON parsing is involved.

### 3.3 High-Level Flow
```
Agent (MCP client)
      │
      ├─ stdio ──► FastMCP server
      │               │
      │               ├─ read config (defaults → global → project)
      │               ├─ validate target path (security check)
      │               ├─ build ProspectorConfig programmatically
      │               ├─ run Prospector API via asyncio.to_thread (with timeout)
      │               ├─ map Message objects to structured dicts
      │               └─ return structured result
      │
      └─ SSE ──────► (same server, different transport)
```

## 4. MCP Interface

### 4.1 Tools

#### `prospector.run`
Run Prospector on a file or directory.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `target` | `string` | Yes | Absolute or relative path to a Python file or directory. |
| `profile` | `string` | No | Prospector profile to use (e.g., `full`, `doc_warnings`). Overrides config. |
| `strictness` | `string` | No | One of `verylow`, `low`, `medium`, `high`, `veryhigh`. Overrides config. |

**Returns:**
A structured object:
```json
{
  "success": true,
  "summary": {
    "message_count": 12,
    "modules_checked": 5,
    "files_checked": 10
  },
  "messages": [
    {
      "source": "pylint",
      "code": "C0301",
      "location": {
        "path": "src/foo.py",
        "line": 42,
        "character": 80
      },
      "message": "Line too long (95/79)",
      "severity": "convention"
    }
  ],
  "execution_time": 1.23
}
```

**Error response:**
```json
{
  "success": false,
  "error": "description",
  "messages": []
}
```

#### `prospector.check_ready`
Check if Prospector is installed and accessible.

**Returns:**
```json
{
  "ready": true,
  "version": "1.13.0",
  "available_profiles": ["default", "full", "doc_warnings", "no_test_warnings"]
}
```

### 4.2 Resources (optional / future)
- `config://prospector.toml` — expose effective configuration for debugging.

### 4.3 Prompts (optional / future)
- `prospector/explain` — provide a message object and get an LLM-friendly explanation template.

## 5. Configuration System

Philosophy: **good defaults, zero config for 80% of users**.

### 5.1 Layering (priority: bottom → top)
1. **Built-in defaults** (hardcoded in the server).
2. **Global config** — `~/.config/prospector-mcp/config.toml`.
3. **Project config** — `.prospector-mcp.toml` in the target project's root (detected by nearest `.git` or CWD).

### 5.2 Configuration Format: TOML
Use `tomllib` (stdlib since Python 3.11).

Example `.prospector-mcp.toml`:
```toml
[prospector]
# Timeout in seconds for a single Prospector run
timeout = 60

# Default strictness if not overridden by the tool call
strictness = "medium"

# Additional paths to ignore beyond .gitignore and defaults
ignore = [".tox", "build", "dist"]

# Default profile
profile = "default"

[server]
# Default transport when running directly
# Can be "stdio" or "sse"
transport = "stdio"

# SSE bind address (only used when transport = "sse")
host = "127.0.0.1"
port = 8080
```

### 5.3 Built-in Defaults
```toml
[prospector]
timeout = 60
strictness = "medium"
profile = "default"
ignore = [".git", "__pycache__", ".venv", "venv", ".env", "env"]
respect_gitignore = true
```

## 6. Security Model

### 6.1 Path Validation
- Reject targets outside the working directory unless explicitly allowed.
- Never follow symlinks outside the project root.
- If `target` is absolute, ensure it resolves within the allowed workspace.

### 6.2 Safe Execution
- Run Prospector via its Python API inside `asyncio.to_thread` with a configurable timeout (default: 60s).
- Cancel the thread/task if it exceeds the timeout.
- Never execute arbitrary code; only Prospector's own tool runners.

### 6.3 Data Exposure
- Do not read or return the contents of `.env`, `*.key`, `*.pem`, or other secret-like files.
- Prospector itself respects `.gitignore` by default; the server enforces this.

## 7. Error Handling

| Scenario | Behavior |
|----------|----------|
| Prospector import fails / not installed | Return `ready: false` on `check_ready`; `run` returns clear error. |
| Target path does not exist | Return `success: false` with `error: "Path not found: ..."`. |
| Target path is outside workspace | Return `success: false` with `error: "Access denied"`. |
| Prospector execution timeout | Cancel task, return `success: false` with `error: "Execution timed out after Ns"`. |
| Prospector raises `FatalProspectorException` | Return `success: false` with the exception message. |
| Prospector tool failure | Return any collected messages plus error context. |

## 8. Project Structure

```
prospector-mcp/
├── src/
│   └── prospector_mcp/
│       ├── __init__.py
│       ├── server.py          # FastMCP app, tool definitions
│       ├── config.py          # Config loading & merging
│       ├── runner.py          # Prospector API invocation & result mapping
│       └── security.py        # Path validation
├── tests/
│   ├── test_server.py
│   ├── test_config.py
│   └── test_runner.py
├── pyproject.toml
├── README.md
└── SPECS.md                  # This file
```

## 9. Dependencies

### 9.1 Runtime
- `fastmcp` — MCP server framework.
- `prospector` — The underlying analysis tool.

### 9.2 Development
- `pytest`
- `pytest-asyncio`
- `ruff` / `mypy` (for linting this project itself)

### 9.3 Distribution
- Package name: `prospector-mcp`
- Entry point: `prospector-mcp = prospector_mcp.server:main`
- Run via: `uvx run prospector-mcp` (uses `stdio` by default)

## 10. Implementation Plan

| Phase | Task | Priority |
|-------|------|----------|
| 1 | Scaffold project (`pyproject.toml`, src layout) | High |
| 2 | Implement `config.py` with layered TOML loading | High |
| 3 | Implement `security.py` path validation | High |
| 4 | Implement `runner.py` (Prospector API invocation via `asyncio.to_thread` + result mapping) | High |
| 5 | Implement `server.py` with `prospector.run` and `prospector.check_ready` | High |
| 6 | Add stdio + SSE transport support | High |
| 7 | Unit tests for config, security, runner | High |
| 8 | Integration test with a sample Python project | Medium |
| 9 | README with install (`uvx`) and usage instructions | Medium |
| 10 | Publish to PyPI | Low (future) |

## 11. Open Questions / Future Work

- Should we cache Prospector results per-file for a short duration?
- Should we expose a `prospector.profiles` tool to list available profiles?
- Should we support `.prospector.yaml` in addition to TOML for configuration?
- SSE mode: should we support API key authentication?
- **API integration**: Prospector's `ProspectorConfig` uses `setoptconf` which reads CLI arguments by default. How do we best inject programmatic parameters (paths, profile, strictness) without relying on `sys.argv`? Options: patch `sys.argv` temporarily, monkey-patch `cfg.build_default_sources()`, or construct a `setoptconf.Configuration` manually.
- **Thread safety**: Prospector tools (pylint, etc.) may not be thread-safe. Should we use a process pool or file-based locking instead of `asyncio.to_thread`?

---

**Status:** Draft  
**Next step:** Create the project scaffold and implement Phase 1–3.
