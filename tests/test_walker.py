"""Tests for the package walker."""

from __future__ import annotations

from pathlib import Path

import pytest

from layup_parser.parser.python.walker import walk_package

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PKG = FIXTURES / "sample_pkg"


class TestWalkPackage:
    def test_returns_parsed_package(self):
        pkg = walk_package(SAMPLE_PKG)
        assert pkg.name == "sample_pkg"
        assert pkg.root_path == str(SAMPLE_PKG.resolve())

    def test_finds_all_modules(self):
        pkg = walk_package(SAMPLE_PKG)
        names = {m.name for m in pkg.modules}
        # Top-level init treated as the package itself
        assert "sample_pkg" in names
        assert "sample_pkg.animals" in names
        # Sub-package modules
        assert "sample_pkg.subpkg" in names
        assert "sample_pkg.subpkg.vehicles" in names

    def test_module_count(self):
        pkg = walk_package(SAMPLE_PKG)
        # sample_pkg (init), sample_pkg.animals, sample_pkg.subpkg (init), sample_pkg.subpkg.vehicles
        assert len(pkg.modules) == 4

    def test_module_ids_are_unique(self):
        pkg = walk_package(SAMPLE_PKG)
        ids = [m.id for m in pkg.modules]
        assert len(ids) == len(set(ids))

    def test_module_ids_no_dots(self):
        """IDs must not contain dots (they become JSON keys / diagram IDs)."""
        pkg = walk_package(SAMPLE_PKG)
        for mod in pkg.modules:
            assert "." not in mod.id, f"Module ID contains dot: {mod.id}"

    def test_file_paths_exist(self):
        pkg = walk_package(SAMPLE_PKG)
        for mod in pkg.modules:
            assert Path(mod.file_path).is_file(), f"Missing file: {mod.file_path}"

    def test_modules_have_no_classes_yet(self):
        """Walker does not extract classes — that's the extractor's job."""
        pkg = walk_package(SAMPLE_PKG)
        for mod in pkg.modules:
            assert mod.classes == []

    def test_invalid_path_raises(self):
        with pytest.raises(ValueError, match="not a directory"):
            walk_package("/nonexistent/path/xyz")

    def test_non_package_raises(self):
        with pytest.raises(ValueError, match="not a Python package"):
            walk_package(FIXTURES)  # fixtures dir has no __init__.py

    def test_custom_ignore(self):
        """Modules inside an ignored directory are excluded."""
        pkg = walk_package(SAMPLE_PKG, ignore=frozenset({"subpkg"}))
        names = {m.name for m in pkg.modules}
        assert "sample_pkg.subpkg.vehicles" not in names
        assert "sample_pkg.animals" in names

    def test_pycache_excluded_by_default(self, tmp_path):
        """__pycache__ directories are never walked."""
        # Create a minimal package with a __pycache__ dir
        (tmp_path / "__init__.py").touch()
        (tmp_path / "mod.py").touch()
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "mod.cpython-312.pyc").touch()
        # Should not raise and should not include __pycache__ entries
        pkg = walk_package(tmp_path)
        for mod in pkg.modules:
            assert "__pycache__" not in mod.file_path
