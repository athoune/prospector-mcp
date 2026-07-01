"""Tests for config loading and merging."""

from pathlib import Path

import pytest

from prospector_mcp.config import DEFAULTS, _deep_merge, load_config


class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        assert _deep_merge(dict(base), override) == {"a": 1, "b": 3}

    def test_nested_merge(self):
        base = {"x": {"y": 1, "z": 2}}
        override = {"x": {"z": 3}}
        assert _deep_merge(dict(base), override) == {"x": {"y": 1, "z": 3}}

    def test_adds_new_keys(self):
        base = {"a": 1}
        override = {"b": 2}
        assert _deep_merge(dict(base), override) == {"a": 1, "b": 2}


class TestLoadConfig:
    def test_returns_defaults_when_no_files(self, tmp_path: Path):
        config = load_config(tmp_path)
        assert config["prospector"]["timeout"] == DEFAULTS["prospector"]["timeout"]
        assert config["prospector"]["strictness"] == DEFAULTS["prospector"]["strictness"]

    def test_merges_project_config(self, tmp_path: Path):
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        (project_root / ".git").mkdir()
        config_file = project_root / ".prospector-mcp.toml"
        config_file.write_text(
            '[prospector]\ntimeout = 120\nstrictness = "high"\n'
        )
        target = project_root / "src"
        target.mkdir()

        config = load_config(target)
        assert config["prospector"]["timeout"] == 120
        assert config["prospector"]["strictness"] == "high"
        # Other defaults are preserved.
        assert config["prospector"]["profile"] == DEFAULTS["prospector"]["profile"]
