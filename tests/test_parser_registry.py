"""Tests for the parser registry and PythonParser."""

from __future__ import annotations

from pathlib import Path

import pytest

from layup_python.parser import SUPPORTED_LANGUAGES, get_parser
from layup_python.parser.base import LanguageParser
from layup_python.parser.python import PythonParser

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PKG = FIXTURES / "sample_pkg"


class TestSupportedLanguages:
    def test_python_is_supported(self):
        assert "python" in SUPPORTED_LANGUAGES

    def test_is_tuple(self):
        assert isinstance(SUPPORTED_LANGUAGES, tuple)

    def test_is_sorted(self):
        assert list(SUPPORTED_LANGUAGES) == sorted(SUPPORTED_LANGUAGES)


class TestGetParser:
    def test_returns_python_parser(self):
        parser = get_parser("python")
        assert isinstance(parser, PythonParser)

    def test_returned_parser_satisfies_protocol(self):
        """get_parser must return an object that satisfies LanguageParser."""
        parser = get_parser("python")
        assert isinstance(parser, LanguageParser)

    def test_unsupported_language_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            get_parser("cobol")

    def test_error_message_lists_supported_languages(self):
        with pytest.raises(ValueError, match="python"):
            get_parser("fortran")

    def test_returns_fresh_instance_each_call(self):
        """Each call returns a new parser instance (no shared state)."""
        p1 = get_parser("python")
        p2 = get_parser("python")
        assert p1 is not p2


class TestPythonParserProtocolCompliance:
    def test_has_parse_method(self):
        parser = PythonParser()
        assert callable(getattr(parser, "parse", None))

    def test_isinstance_language_parser(self):
        assert isinstance(PythonParser(), LanguageParser)


class TestPythonParserParse:
    def test_returns_parsed_package(self):
        parser = PythonParser()
        pkg = parser.parse(SAMPLE_PKG)
        assert pkg.name == "sample_pkg"

    def test_modules_populated(self):
        parser = PythonParser()
        pkg = parser.parse(SAMPLE_PKG)
        names = {m.name for m in pkg.modules}
        assert "sample_pkg.animals" in names
        assert "sample_pkg.subpkg.vehicles" in names

    def test_classes_extracted(self):
        """parse() must fully populate classes — not just discover files."""
        parser = PythonParser()
        pkg = parser.parse(SAMPLE_PKG)
        all_class_names = {
            cls.name for mod in pkg.modules for cls in mod.classes
        }
        assert "Dog" in all_class_names
        assert "Animal" in all_class_names
        assert "AnimalKind" in all_class_names

    def test_ignore_parameter_forwarded(self):
        parser = PythonParser()
        pkg = parser.parse(SAMPLE_PKG, ignore=frozenset({"subpkg"}))
        names = {m.name for m in pkg.modules}
        assert "sample_pkg.subpkg.vehicles" not in names
        assert "sample_pkg.animals" in names

    def test_invalid_root_raises_value_error(self):
        parser = PythonParser()
        with pytest.raises(ValueError):
            parser.parse(FIXTURES)  # no __init__.py

    def test_nonexistent_root_raises_value_error(self):
        parser = PythonParser()
        with pytest.raises(ValueError):
            parser.parse(Path("/nonexistent/path/xyz"))

    def test_accepts_path_object(self):
        parser = PythonParser()
        pkg = parser.parse(Path(SAMPLE_PKG))
        assert pkg.name == "sample_pkg"
