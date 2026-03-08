"""Python implementation of the :class:`~layup_parser.parser.base.LanguageParser` protocol.

:class:`PythonParser` composes the Python-specific walker and AST extractor
into a single :meth:`parse` call, satisfying the language-agnostic
:class:`~layup_parser.parser.base.LanguageParser` protocol expected by the
rest of the pipeline.
"""

from __future__ import annotations

from pathlib import Path

from layup_parser.models import ParsedPackage
from layup_parser.parser.python.extractor import extract_module
from layup_parser.parser.python.walker import walk_package


class PythonParser:
    """LanguageParser implementation for Python packages.

    Uses Python's stdlib :mod:`ast` module to parse source files and the
    built-in package walker to discover ``.py`` files within a package tree
    (a directory rooted at an ``__init__.py``).
    """

    def parse(
        self,
        root: Path,
        *,
        ignore: frozenset[str] | None = None,
    ) -> ParsedPackage:
        """Walk a Python package rooted at *root* and extract all classes.

        Parameters
        ----------
        root:
            Path to the root Python package directory (must contain
            ``__init__.py``).
        ignore:
            Additional directory names to skip beyond the built-in exclusion
            list (see :func:`~layup_parser.parser.python.walker.walk_package`).

        Returns
        -------
        ParsedPackage
            Fully-populated package with all classes and members extracted.

        Raises
        ------
        ValueError
            If *root* is not a valid Python package directory.
        """
        package = walk_package(root, ignore=ignore)
        for mod in package.modules:
            extract_module(mod)
        return package
