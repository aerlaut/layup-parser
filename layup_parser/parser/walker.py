"""Backward-compatibility shim.

The Python package walker has moved to
:mod:`layup_parser.parser.python.walker`.  This module re-exports the public
symbol so that any existing direct imports continue to work.

.. deprecated::
    Import directly from :mod:`layup_parser.parser.python.walker` instead.
"""

from layup_parser.parser.python.walker import walk_package  # noqa: F401

__all__ = ["walk_package"]
