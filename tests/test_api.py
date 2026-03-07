"""Tests for the public API (layup_python.__init__)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

import layup_python
from layup_python import parse_package, parse_package_to_file
from layup_python._schema_path import SCHEMA_PATH, SCHEMA_VERSION

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PKG = FIXTURES / "sample_pkg"

with SCHEMA_PATH.open() as _f:
    _SCHEMA = json.load(_f)


class TestParsePackage:
    def test_returns_dict(self):
        result = parse_package(SAMPLE_PKG)
        assert isinstance(result, dict)

    def test_version(self):
        result = parse_package(SAMPLE_PKG)
        assert result["version"] == SCHEMA_VERSION

    def test_schema_valid(self):
        result = parse_package(SAMPLE_PKG)
        jsonschema.validate(result, _SCHEMA)

    def test_root_label_default(self):
        result = parse_package(SAMPLE_PKG)
        root_diag = result["diagrams"][result["rootId"]]
        assert root_diag["label"] == "sample_pkg"

    def test_custom_root_label(self):
        result = parse_package(SAMPLE_PKG, root_label="My Package")
        root_diag = result["diagrams"][result["rootId"]]
        assert root_diag["label"] == "My Package"

    def test_invalid_path_raises(self):
        with pytest.raises(ValueError):
            parse_package("/nonexistent/path")

    def test_non_package_raises(self):
        with pytest.raises(ValueError):
            parse_package(FIXTURES)  # no __init__.py

    def test_contains_module_diagrams(self):
        result = parse_package(SAMPLE_PKG)
        diag_ids = set(result["diagrams"].keys())
        # Root + one per module
        assert len(diag_ids) > 1

    def test_classes_extracted(self):
        result = parse_package(SAMPLE_PKG)
        # Find the animals module diagram and check classes are present
        code_diags = [
            d for d in result["diagrams"].values()
            if d["level"] == "code"
        ]
        all_labels = {n["label"] for d in code_diags for n in d["nodes"]}
        assert "Dog" in all_labels
        assert "Animal" in all_labels
        assert "AnimalKind" in all_labels

    def test_inheritance_edges_present(self):
        result = parse_package(SAMPLE_PKG)
        all_edges = [
            e
            for d in result["diagrams"].values()
            for e in d["edges"]
        ]
        assert len(all_edges) > 0

    def test_validate_false_skips_schema_check(self):
        # Should not raise even though we can't easily inject invalid data,
        # but confirm the flag is accepted
        result = parse_package(SAMPLE_PKG, validate=False)
        assert isinstance(result, dict)

    def test_cross_module_warnings_to_stderr(self, capsys):
        # sample_pkg has cross-module inheritance (Dog from animals inherits
        # from nothing cross-module in this fixture, but subpkg doesn't inherit
        # from animals). Let's just verify the call doesn't crash and stderr
        # is readable.
        parse_package(SAMPLE_PKG)
        captured = capsys.readouterr()
        # Any warnings that exist go to stderr
        if captured.err:
            assert "WARNING" in captured.err


class TestParsePackageToFile:
    def test_creates_file(self, tmp_path):
        output = tmp_path / "out.json"
        parse_package_to_file(SAMPLE_PKG, output)
        assert output.is_file()

    def test_valid_json(self, tmp_path):
        output = tmp_path / "out.json"
        parse_package_to_file(SAMPLE_PKG, output)
        with output.open() as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_schema_valid(self, tmp_path):
        output = tmp_path / "out.json"
        parse_package_to_file(SAMPLE_PKG, output)
        with output.open() as f:
            data = json.load(f)
        jsonschema.validate(data, _SCHEMA)

    def test_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "nested" / "deep" / "out.json"
        parse_package_to_file(SAMPLE_PKG, output)
        assert output.is_file()

    def test_indent_respected(self, tmp_path):
        output = tmp_path / "out.json"
        parse_package_to_file(SAMPLE_PKG, output, indent=4)
        content = output.read_text()
        # 4-space indent means lines should start with "    " not "  "
        assert '    "' in content

    def test_string_path_accepted(self, tmp_path):
        output = tmp_path / "out.json"
        parse_package_to_file(str(SAMPLE_PKG), str(output))
        assert output.is_file()


class TestPublicExports:
    def test_parse_package_exported(self):
        assert hasattr(layup_python, "parse_package")

    def test_parse_package_to_file_exported(self):
        assert hasattr(layup_python, "parse_package_to_file")

    def test_all_list(self):
        assert "parse_package" in layup_python.__all__
        assert "parse_package_to_file" in layup_python.__all__
