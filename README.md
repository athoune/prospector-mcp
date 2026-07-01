# Prospector MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that exposes [Prospector](https://github.com/prospector-dev/prospector) — the Python static analysis tool — through its **native Python API**.

## Features

- Run Prospector on a single file or an entire directory.
- Return structured, machine-readable results (messages with severity, location, rule code).
- Layered TOML configuration with sensible defaults.
- Supports both `stdio` and `SSE` transports via [FastMCP](https://github.com/jlowin/fastmcp).
- Secure by default: respects `.gitignore`, ignores `.env` / `.venv`, validates paths, enforces timeouts.

## Installation

### Via `uvx` (recommended)

```bash
uvx run prospector-mcp
```

### Via `pip`

```bash
pip install prospector-mcp
prospector-mcp
```

### Development setup

```bash
git clone https://github.com/yourname/prospector-mcp.git
cd prospector-mcp
pip install -e ".[dev]"
pytest
```

## Usage

### Claude Desktop / OpenCode

Add the server to your MCP settings:

```json
{
  "mcpServers": {
    "prospector": {
      "command": "uvx",
      "args": ["run", "prospector-mcp"]
    }
  }
}
```

### SSE transport

```bash
prospector-mcp --transport sse
# or
prospector-mcp --sse
```

## Configuration

Configuration is layered (later layers override earlier ones):

1. **Built-in defaults**
2. **Global config**: `~/.config/prospector-mcp/config.toml`
3. **Project config**: `.prospector-mcp.toml` in the project root

### Example `.prospector-mcp.toml`

```toml
[prospector]
timeout = 60
strictness = "medium"
profile = "default"
ignore = [".tox", "build", "dist"]

[server]
transport = "stdio"
```

## Tools

### `prospector.run`

Run Prospector on a target path.

**Parameters:**
- `target` (string, required): Path to a Python file or directory.
- `profile` (string, optional): Override the Prospector profile.
- `strictness` (string, optional): Override strictness (`verylow` to `veryhigh`).

**Returns:** Structured dict with `summary`, `messages`, and `execution_time`.

### `prospector.check_ready`

Check if Prospector is installed and available.

## License

MIT
