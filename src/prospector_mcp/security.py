"""Path validation utilities for prospector-mcp."""

from pathlib import Path


def find_project_root(start: Path) -> Path:
    """Walk up from *start* looking for a .git directory.

    Returns the directory containing .git, or *start.resolve()* if none
    is found.
    """
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start.resolve()


def validate_target(target: str, workspace: Path) -> Path:
    """Resolve *target* and ensure it is safe to access.

    Checks:
    - Path must exist.
    - Path must be inside *workspace* (no directory traversal).
    - Symlinks that escape *workspace* are rejected.

    Raises:
        FileNotFoundError: if the path does not exist.
        PermissionError: if the path is outside the workspace.

    Returns:
        The resolved absolute Path.
    """
    workspace = workspace.resolve()
    raw = Path(target)

    if not raw.exists():
        raise FileNotFoundError(f"Path not found: {target}")

    resolved = raw.resolve()

    # Reject symlinks that point outside the workspace.
    try:
        real = raw.resolve(strict=True)
    except (OSError, ValueError):
        real = resolved

    if not str(resolved).startswith(str(workspace)):
        raise PermissionError(f"Access denied: {resolved} is outside workspace {workspace}")

    if not str(real).startswith(str(workspace)):
        raise PermissionError(f"Access denied: symlink {resolved} escapes workspace {workspace}")

    return resolved
