"""Backward-compatibility shim.

The Python AST extractor has moved to
:mod:`layup_python.parser.python.extractor`.  This module re-exports the
public symbol so that any existing direct imports continue to work.

.. deprecated::
    Import directly from :mod:`layup_python.parser.python.extractor` instead.
"""

from layup_python.parser.python.extractor import extract_module  # noqa: F401

__all__ = ["extract_module"]
