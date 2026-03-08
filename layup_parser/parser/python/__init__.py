"""Python language parser sub-package.

Public surface
--------------
- :class:`PythonParser` — walks Python packages and extracts classes via the
  stdlib :mod:`ast` module.
- :func:`~layup_parser.parser.python.walker.walk_package` — low-level package
  discovery (re-exported for convenience / direct use).
- :func:`~layup_parser.parser.python.extractor.extract_module` — low-level
  AST extraction (re-exported for convenience / direct use).
"""

from layup_parser.parser.python.extractor import extract_module
from layup_parser.parser.python.parser import PythonParser
from layup_parser.parser.python.walker import walk_package

__all__ = ["PythonParser", "walk_package", "extract_module"]
