"""Dogfooding test: analyse this very project with the MCP server."""

from pathlib import Path

import pytest

from prospector_mcp.server import prospector_run


class TestDogfooding:
    """Run the server on its own source code — "eat your own dogfood"."""

    @pytest.mark.asyncio
    async def test_analyses_own_source(self):
        """The server should successfully analyse src/prospector_mcp/ and return structured data."""
        project_root = Path(__file__).resolve().parent.parent
        source_dir = project_root / "src" / "prospector_mcp"

        result = await prospector_run(
            target=str(source_dir),
            profile="default",
            strictness="medium",
        )

        assert result["success"] is True
        assert "messages" in result
        assert "summary" in result
        assert isinstance(result["messages"], list)

        # Every message must have the expected schema.
        for msg in result["messages"]:
            assert "source" in msg
            assert "code" in msg
            assert "location" in msg
            assert "path" in msg["location"]
            assert "line" in msg["location"]
            assert "message" in msg

    @pytest.mark.asyncio
    async def test_respects_project_config(self):
        """The project has a .prospector.yaml in its root; the server must honour it."""
        project_root = Path(__file__).resolve().parent.parent
        source_dir = project_root / "src" / "prospector_mcp"

        result = await prospector_run(
            target=str(source_dir),
            profile="default",
            strictness="medium",
        )

        assert result["success"] is True

        # The project's .prospector.yaml disables doc/member/test warnings and
        # sets strictness profiles.  We should not see messages from those
        # categories.
        for msg in result["messages"]:
            msg_text = msg["message"].lower()
            assert "docstring" not in msg_text
            assert "member" not in msg_text
            assert "test" not in msg_text or "test" in msg["source"].lower()
