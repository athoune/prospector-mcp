"""Tests for path validation utilities."""

from pathlib import Path

import pytest

from prospector_mcp.security import validate_target


class TestValidateTarget:
    def test_allows_valid_file(self, tmp_path: Path):
        file = tmp_path / "foo.py"
        file.write_text("x = 1\n")
        result = validate_target(str(file), tmp_path)
        assert result == file.resolve()

    def test_allows_valid_directory(self, tmp_path: Path):
        sub = tmp_path / "src"
        sub.mkdir()
        result = validate_target(str(sub), tmp_path)
        assert result == sub.resolve()

    def test_rejects_nonexistent(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            validate_target(str(tmp_path / "missing.py"), tmp_path)

    def test_rejects_outside_workspace(self, tmp_path: Path):
        outside = Path("/tmp")
        with pytest.raises(PermissionError):
            validate_target(str(outside), tmp_path)

    def test_rejects_symlink_escape(self, tmp_path: Path):
        real = tmp_path / "real"
        real.mkdir()
        outside = Path("/tmp")
        link = tmp_path / "link"
        link.symlink_to(outside)
        with pytest.raises(PermissionError):
            validate_target(str(link), tmp_path)
