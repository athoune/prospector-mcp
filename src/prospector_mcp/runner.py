"""Invoke Prospector via its native Python API and map results."""

import asyncio
import sys
from pathlib import Path
from typing import Any

from prospector import tools as prospector_tools
from prospector.config import ProspectorConfig
from prospector.exceptions import FatalProspectorException
from prospector.run import Prospector


def _patch_argv(
    target: Path,
    profile: str | None,
    strictness: str | None,
    tools: str | list[str] | None,
) -> list[str]:
    """Build a fake sys.argv for setoptconf so ProspectorConfig picks up our parameters."""
    argv = ["prospector", str(target)]
    # Only pass --profile if it is explicitly overridden (non-default).
    # This keeps Prospector's auto-detection of .prospector.yaml intact.
    if profile and profile != "default":
        argv += ["--profile", profile]
    if strictness:
        argv += ["--strictness", strictness]

    # Activate tools explicitly. "all" means every tool that is installed.
    if tools == "all":
        for tool_name in prospector_tools.TOOLS:
            argv += ["-t", tool_name]
    elif isinstance(tools, list):
        for tool_name in tools:
            argv += ["-t", tool_name]

    return argv


def _run_sync(target: Path, config: dict) -> dict[str, Any]:
    """Synchronous Prospector execution — meant to be called inside asyncio.to_thread."""
    project_root = config.get("_project_root", target if target.is_dir() else target.parent)
    profile = config["prospector"].get("profile")
    strictness = config["prospector"].get("strictness")
    tools = config["prospector"].get("tools")

    old_argv = sys.argv[:]
    try:
        sys.argv = _patch_argv(target, profile, strictness, tools)
        pconfig = ProspectorConfig(workdir=project_root)
    finally:
        sys.argv = old_argv

    prospector = Prospector(pconfig)
    prospector.execute()

    messages = []
    for msg in prospector.get_messages():
        loc = msg.location
        messages.append(
            {
                "source": msg.source,
                "code": msg.code,
                "location": {
                    "path": str(loc.path) if loc.path else None,
                    "line": loc.line,
                    "character": loc.character,
                },
                "message": msg.message,
            }
        )

    summary = prospector.get_summary() or {}
    return {
        "success": True,
        "summary": summary,
        "messages": messages,
        "execution_time": summary.get("time_taken"),
    }


async def run_prospector(target: Path, config: dict) -> dict[str, Any]:
    """Run Prospector on *target* with the given merged *config*.

    Execution is moved to a thread and guarded by *config["prospector"]["timeout"]*.
    """
    timeout = config["prospector"].get("timeout", 60)

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_sync, target, config),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Execution timed out after {timeout}s",
            "messages": [],
        }
    except FatalProspectorException as exc:
        return {
            "success": False,
            "error": f"Prospector fatal error: {exc}",
            "messages": [],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Unexpected error: {exc}",
            "messages": [],
        }
