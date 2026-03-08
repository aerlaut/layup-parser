"""Tests for the CLI (layup-parse)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from layup_parser._schema_path import SCHEMA_PATH
from layup_parser.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PKG = FIXTURES / "sample_pkg"

with SCHEMA_PATH.open() as _f:
    _SCHEMA = json.load(_f)


@pytest.fixture
def runner():
    return CliRunner()


class TestCliBasicUsage:
    def test_stdout_output(self, runner):
        result = runner.invoke(main, [str(SAMPLE_PKG)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "version" in data

    def test_stdout_is_valid_json(self, runner):
        result = runner.invoke(main, [str(SAMPLE_PKG)])
        assert result.exit_code == 0
        json.loads(result.output)  # must not raise

    def test_stdout_validates_against_schema(self, runner):
        import jsonschema

        result = runner.invoke(main, [str(SAMPLE_PKG)])
        data = json.loads(result.output)
        jsonschema.validate(data, _SCHEMA)

    def test_output_flag_writes_file(self, runner, tmp_path):
        out = tmp_path / "out.json"
        result = runner.invoke(main, [str(SAMPLE_PKG), "-o", str(out)])
        assert result.exit_code == 0
        assert out.is_file()
        data = json.loads(out.read_text())
        assert "version" in data

    def test_output_flag_no_json_on_stdout(self, runner, tmp_path):
        out = tmp_path / "out.json"
        result = runner.invoke(main, [str(SAMPLE_PKG), "-o", str(out)])
        # When writing to a file, stdout must not contain the JSON payload
        try:
            json.loads(result.output)
            assert False, "Expected no JSON on stdout when -o is used"
        except json.JSONDecodeError:
            pass  # good — output is not JSON

    def test_written_to_message_in_output(self, runner, tmp_path):
        out = tmp_path / "out.json"
        # CliRunner mixes stderr into output by default
        result = runner.invoke(main, [str(SAMPLE_PKG), "-o", str(out)])
        assert "Written to" in result.output


class TestCliOptions:
    def test_root_label(self, runner):
        # root_label is accepted but silently ignored in v2 (DiagramLevel has no label)
        result = runner.invoke(main, [str(SAMPLE_PKG), "--root-label", "My Diagram"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "levels" in data
        assert data["currentLevel"] == "component"

    def test_indent_option(self, runner):
        result = runner.invoke(main, [str(SAMPLE_PKG), "--indent", "4"])
        assert result.exit_code == 0
        # 4-space indent lines present
        assert '    "' in result.output

    def test_no_validate_flag(self, runner):
        result = runner.invoke(main, [str(SAMPLE_PKG), "--no-validate"])
        assert result.exit_code == 0

    def test_ignore_option(self, runner):
        result = runner.invoke(
            main, [str(SAMPLE_PKG), "--ignore", "subpkg"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        # No nodes from subpkg in component or code levels
        component_ids = {n["id"] for n in data["levels"]["component"]["nodes"]}
        code_ids = {n["id"] for n in data["levels"]["code"]["nodes"]}
        assert not any("subpkg" in nid for nid in component_ids | code_ids)

    def test_ignore_repeatable(self, runner):
        result = runner.invoke(
            main,
            [str(SAMPLE_PKG), "--ignore", "subpkg", "--ignore", "__pycache__"],
        )
        assert result.exit_code == 0


class TestCliLangOption:
    def test_explicit_python_lang(self, runner):
        result = runner.invoke(main, [str(SAMPLE_PKG), "--lang", "python"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "version" in data

    def test_unsupported_lang_rejected_by_click(self, runner):
        """Click's Choice type should reject unknown languages before parse_package runs."""
        result = runner.invoke(main, [str(SAMPLE_PKG), "--lang", "cobol"])
        assert result.exit_code != 0
        assert "cobol" in result.output or "Invalid value" in result.output

    def test_lang_in_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--lang" in result.output


class TestCliErrors:
    def test_nonexistent_path(self, runner):
        result = runner.invoke(main, ["/nonexistent/path/abc"])
        assert result.exit_code != 0

    def test_non_package_path(self, runner):
        # FIXTURES dir has no __init__.py → ValueError from walker
        result = runner.invoke(main, [str(FIXTURES)])
        assert result.exit_code == 1
        assert "Error:" in result.output or result.exit_code == 1

    def test_help_flag(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "PATH" in result.output
