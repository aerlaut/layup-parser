"""Tests for the public API (layup_parser.__init__)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

import layup_parser
from layup_parser import parse_package, parse_package_to_file
from layup_parser._schema_path import SCHEMA_PATH, SCHEMA_VERSION

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

    def test_export_type(self):
        result = parse_package(SAMPLE_PKG)
        assert result["exportType"] == "node-subtree"

    def test_root_level_is_component(self):
        result = parse_package(SAMPLE_PKG)
        assert result["rootLevel"] == "component"

    def test_component_and_code_levels_present(self):
        result = parse_package(SAMPLE_PKG)
        assert "component" in result["levels"]
        assert "code" in result["levels"]

    def test_invalid_path_raises(self):
        with pytest.raises(ValueError):
            parse_package("/nonexistent/path")

    def test_non_package_raises(self):
        with pytest.raises(ValueError):
            parse_package(FIXTURES)  # no __init__.py

    def test_contains_module_nodes(self):
        result = parse_package(SAMPLE_PKG)
        # Component level should have at least one module node
        assert len(result["levels"]["component"]["nodes"]) > 0

    def test_classes_extracted(self):
        result = parse_package(SAMPLE_PKG)
        # All class nodes are in the unified code level
        all_labels = {n["label"] for n in result["levels"]["code"]["nodes"]}
        assert "Dog" in all_labels
        assert "Animal" in all_labels
        assert "AnimalKind" in all_labels

    def test_inheritance_edges_present(self):
        result = parse_package(SAMPLE_PKG)
        all_edges = result["levels"]["code"]["edges"]
        assert len(all_edges) > 0

    def test_validate_false_skips_schema_check(self):
        # Should not raise even though we can't easily inject invalid data,
        # but confirm the flag is accepted
        result = parse_package(SAMPLE_PKG, validate=False)
        assert isinstance(result, dict)

    def test_cross_module_warnings_to_stderr(self, capsys):
        parse_package(SAMPLE_PKG)
        captured = capsys.readouterr()
        # Any warnings that exist go to stderr
        if captured.err:
            assert "WARNING" in captured.err

    def test_usage_edges_present(self):
        """Integration: parsed fixture should contain usage (dashed) edges."""
        result = parse_package(SAMPLE_PKG)
        all_edges = result["levels"]["code"]["edges"]
        dashed_edges = [e for e in all_edges if e.get("lineStyle") == "dashed"]
        assert len(dashed_edges) > 0

    def test_usage_edges_have_open_arrow_marker(self):
        """All dashed edges should carry open-arrow markerEnd."""
        result = parse_package(SAMPLE_PKG)
        all_edges = result["levels"]["code"]["edges"]
        for e in all_edges:
            if e.get("lineStyle") == "dashed":
                assert e["markerEnd"] == "open-arrow"


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


class TestParsePackageLang:
    def test_explicit_python_lang(self):
        """Passing lang='python' explicitly must work identically to the default."""
        result = parse_package(SAMPLE_PKG, lang="python")
        assert isinstance(result, dict)
        assert result["rootLevel"] == "component"

    def test_unsupported_lang_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            parse_package(SAMPLE_PKG, lang="cobol")

    def test_lang_forwarded_to_file(self, tmp_path):
        """parse_package_to_file must forward lang to parse_package."""
        output = tmp_path / "out.json"
        parse_package_to_file(SAMPLE_PKG, output, lang="python")
        assert output.is_file()
        data = json.loads(output.read_text())
        assert "version" in data

    def test_unsupported_lang_to_file_raises(self, tmp_path):
        output = tmp_path / "out.json"
        with pytest.raises(ValueError, match="Unsupported language"):
            parse_package_to_file(SAMPLE_PKG, output, lang="cobol")


class TestPublicExports:
    def test_parse_package_exported(self):
        assert hasattr(layup_parser, "parse_package")

    def test_parse_package_to_file_exported(self):
        assert hasattr(layup_parser, "parse_package_to_file")

    def test_all_list(self):
        assert "parse_package" in layup_parser.__all__
        assert "parse_package_to_file" in layup_parser.__all__
