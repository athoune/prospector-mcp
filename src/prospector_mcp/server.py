"""FastMCP server exposing Prospector tools."""

import importlib
import sys
from pathlib import Path

from fastmcp import FastMCP

from prospector_mcp.config import find_project_root, load_config
from prospector_mcp.runner import run_prospector
from prospector_mcp.security import validate_target

mcp = FastMCP("prospector")


@mcp.tool()
async def prospector_run(
    target: str,
    profile: str | None = None,
    strictness: str | None = None,
) -> dict:
    """Run Prospector static analysis on a file or directory.

    Args:
        target: Absolute or relative path to a Python file or directory.
        profile: Prospector profile to use (overrides config).
        strictness: Strictness level (overrides config).

    Returns:
        Structured dict with summary, messages, and execution metadata.

    """
    raw_target = Path(target)
    project_root = find_project_root(raw_target if raw_target.is_dir() else raw_target.parent)

    # Load layered configuration.
    config = load_config(raw_target)

    # Apply tool-level overrides.
    if profile:
        config["prospector"]["profile"] = profile
    if strictness:
        config["prospector"]["strictness"] = strictness

    # Inject project_root so runner knows where to anchor the workdir.
    config["_project_root"] = project_root

    # Validate target is safe.
    try:
        validated = validate_target(target, project_root)
    except (FileNotFoundError, PermissionError) as exc:
        return {"success": False, "error": str(exc), "messages": []}

    return await run_prospector(validated, config)


@mcp.tool()
async def prospector_check_ready() -> dict:
    """Check whether Prospector is installed and report its version."""
    try:
        prospector = importlib.import_module("prospector")
        version = getattr(prospector, "__version__", "unknown")
    except Exception:
        return {
            "ready": False,
            "version": None,
            "available_profiles": [],
        }

    # Profiles shipped with prospector.
    available = [
        "default",
        "full",
        "doc_warnings",
        "no_test_warnings",
        "member_warnings",
        "strictness_verylow",
        "strictness_low",
        "strictness_medium",
        "strictness_high",
        "strictness_veryhigh",
    ]
    return {
        "ready": True,
        "version": version,
        "available_profiles": available,
    }


def main() -> None:
    """Entry point — supports stdio (default) and SSE transports."""
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]
    elif "--sse" in sys.argv:
        transport = "sse"

    if transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run()


# Explicit references to silence static-analysis tools that do not
# understand FastMCP's decorator-based registration.
_TOOL_REGISTRATION = (prospector_run, prospector_check_ready)

if __name__ == "__main__":
    main()
