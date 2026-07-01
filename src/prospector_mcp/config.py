"""Layered TOML configuration loader for prospector-mcp."""

import tomllib
from pathlib import Path


# Built-in defaults — good out of the box.
DEFAULTS = {
    "prospector": {
        "timeout": 60,
        "strictness": "medium",
        "profile": "default",
        "tools": "all",
        "ignore": [".git", "__pycache__", ".venv", "venv", ".env", "env"],
        "respect_gitignore": True,
    },
    "server": {
        "transport": "stdio",
        "host": "127.0.0.1",
        "port": 8080,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (mutates base)."""
    for key, value in override.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _load_toml(path: Path) -> dict:
    """Load a TOML file if it exists, otherwise return empty dict."""
    if not path.exists():
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, ValueError):
        # Corrupt or unreadable file — skip gracefully.
        return {}


def find_project_root(start: Path) -> Path:
    """Walk up from *start* looking for a .git directory.

    Returns the directory containing .git, or *start* if none is found.
    """
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start.resolve()


def load_config(target_path: Path) -> dict:
    """Return merged configuration for the given target path.

    Priority (low → high):
    1. Built-in defaults
    2. Global config: ``~/.config/prospector-mcp/config.toml``
    3. Project config: ``.prospector-mcp.toml`` in the project root
    """
    config = {section: dict(values) for section, values in DEFAULTS.items()}

    # 2. Global config
    global_config = Path.home() / ".config" / "prospector-mcp" / "config.toml"
    config = _deep_merge(config, _load_toml(global_config))

    # 3. Project config
    project_root = find_project_root(target_path if target_path.is_dir() else target_path.parent)
    project_config = project_root / ".prospector-mcp.toml"
    config = _deep_merge(config, _load_toml(project_config))

    return config
