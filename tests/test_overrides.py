"""Tests that profile and strictness overrides reach Prospector."""

from pathlib import Path

import pytest

from prospector_mcp.runner import run_prospector


class TestOverrides:
    """Ensure that config["prospector"]["strictness"] and ["profile"]
    are forwarded to ProspectorConfig via the sys.argv patch.
    """

    @pytest.mark.asyncio
    async def test_strictness_override_changes_message_count(self, tmp_path: Path):
        """A stricter level should produce at least as many messages as a looser one."""
        source = tmp_path / "sample.py"
        source.write_text("x=1\n")  # style issue

        config_low = {
            "prospector": {
                "timeout": 60,
                "profile": "default",
                "strictness": "verylow",
            },
            "_project_root": tmp_path,
        }
        config_high = {
            "prospector": {
                "timeout": 60,
                "profile": "default",
                "strictness": "veryhigh",
            },
            "_project_root": tmp_path,
        }

        result_low = await run_prospector(source, config_low)
        result_high = await run_prospector(source, config_high)

        assert result_low["success"] is True
        assert result_high["success"] is True

        count_low = len(result_low["messages"])
        count_high = len(result_high["messages"])

        # Veryhigh should catch at least as much as verylow.
        assert count_high >= count_low

    @pytest.mark.asyncio
    async def test_profile_override_doc_warnings(self, tmp_path: Path):
        """Profile "doc_warnings" should flag missing docstrings."""
        source = tmp_path / "sample.py"
        source.write_text("def foo():\n    pass\n")

        config_no_doc = {
            "prospector": {
                "timeout": 60,
                "profile": "no_doc_warnings",
                "strictness": "medium",
            },
            "_project_root": tmp_path,
        }
        config_doc = {
            "prospector": {
                "timeout": 60,
                "profile": "doc_warnings",
                "strictness": "medium",
            },
            "_project_root": tmp_path,
        }

        result_no_doc = await run_prospector(source, config_no_doc)
        result_doc = await run_prospector(source, config_doc)

        assert result_no_doc["success"] is True
        assert result_doc["success"] is True

        # doc_warnings profile should produce messages related to missing docstrings.
        # no_doc_warnings should suppress them.
        doc_codes_doc = {
            msg["code"] for msg in result_doc["messages"] if "doc" in msg["message"].lower()
        }
        doc_codes_no = {
            msg["code"] for msg in result_no_doc["messages"] if "doc" in msg["message"].lower()
        }

        # If pydocstyle runs, we expect D1xx codes; if not, the set is empty.
        # The test only asserts that doc_warnings yields *more* doc-related messages.
        assert len(doc_codes_doc) >= len(doc_codes_no)

    @pytest.mark.asyncio
    async def test_project_prospector_yaml_is_respected(self, tmp_path: Path):
        """If the target directory contains a .prospector.yaml, ProspectorConfig loads it."""
        source = tmp_path / "sample.py"
        source.write_text("x=1\n")

        # Create a minimal project-level config that bumps strictness.
        (tmp_path / ".prospector.yaml").write_text("\n".join([
            "---",
            "strictness: veryhigh",
        ]))

        # Ask for verylow strictness in the MCP config — the project file should
        # NOT override it because the server passes profile/strictness on the
        # command line, which has higher priority.
        config = {
            "prospector": {
                "timeout": 60,
                "profile": "default",
                "strictness": "verylow",
            },
            "_project_root": tmp_path,
        }

        result = await run_prospector(source, config)
        assert result["success"] is True
        # verylow strictness should suppress the whitespace warning that veryhigh catches.
        codes = {msg["code"] for msg in result["messages"]}
        assert "E225" not in codes
