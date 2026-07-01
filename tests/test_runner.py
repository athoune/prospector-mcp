"""Tests for Prospector API invocation."""

import asyncio
from pathlib import Path

import pytest

from prospector_mcp.runner import run_prospector


class TestRunProspector:
    @pytest.mark.asyncio
    async def test_runs_on_simple_file(self, tmp_path: Path):
        # Create a minimal Python file with a deliberate style issue.
        source = tmp_path / "sample.py"
        source.write_text("x=1\n")  # missing spaces around operator

        config = {
            "prospector": {
                "timeout": 60,
                "profile": "default",
                "strictness": "veryhigh",
            },
            "_project_root": tmp_path,
        }

        result = await run_prospector(source, config)

        assert result["success"] is True
        assert "messages" in result
        assert isinstance(result["messages"], list)
        # With veryhigh strictness on missing whitespace, we expect messages.
        assert len(result["messages"]) > 0

        # Validate message structure.
        msg = result["messages"][0]
        assert "source" in msg
        assert "code" in msg
        assert "location" in msg
        assert "message" in msg
        assert "path" in msg["location"]

    @pytest.mark.asyncio
    async def test_respects_timeout(self, tmp_path: Path):
        source = tmp_path / "sample.py"
        source.write_text("x = 1\n")

        config = {
            "prospector": {
                "timeout": 0.001,  # impossibly short
                "profile": "default",
                "strictness": "medium",
            },
            "_project_root": tmp_path,
        }

        result = await run_prospector(source, config)
        assert result["success"] is False
        assert "timed out" in result["error"].lower()
