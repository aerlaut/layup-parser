"""layup-python — Python package parser for Layup diagram import.

Public API
----------
::

    from layup_python import parse_package, parse_package_to_file

    # Returns a DiagramState dict
    diagram = parse_package("/path/to/mypkg")

    # Convenience: write JSON directly to a file
    parse_package_to_file("/path/to/mypkg", "diagram.json")
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from layup_python.emitter.layup import emit_diagram_state
from layup_python.models import ParsedPackage
from layup_python.parser.extractor import extract_module
from layup_python.parser.walker import walk_package
from layup_python.relationships import resolve_inheritance

__all__ = ["parse_package", "parse_package_to_file"]


def parse_package(
    path: str | Path,
    *,
    root_label: str | None = None,
    ignore: frozenset[str] | None = None,
    validate: bool = True,
) -> dict:
    """Parse a Python package and return a Layup ``DiagramState`` dict.

    Parameters
    ----------
    path:
        Root directory of the Python package (must contain ``__init__.py``).
    root_label:
        Optional label for the root component diagram.  Defaults to the
        package directory name.
    ignore:
        Additional directory names to exclude during walking (merged with the
        built-in exclusion list — see :func:`~layup_python.parser.walker.walk_package`).
    validate:
        If ``True`` (default), validate the output against the bundled JSON
        Schema before returning.  Raises :class:`jsonschema.ValidationError`
        on failure.

    Returns
    -------
    dict
        A valid Layup ``DiagramState`` object ready for JSON serialisation.

    Raises
    ------
    ValueError
        If *path* is not a valid Python package directory.
    jsonschema.ValidationError
        If *validate* is ``True`` and the output does not match the schema
        (should never happen — indicates a bug in the emitter).
    """
    # 1. Walk
    package: ParsedPackage = walk_package(path, ignore=ignore)

    # 2. Extract
    for mod in package.modules:
        extract_module(mod)

    # 3. Resolve relationships
    edges, warnings = resolve_inheritance(package)

    # Emit warnings to stderr so stdout stays clean for piping
    for w in warnings:
        print(f"[layup-python] WARNING: {w}", file=sys.stderr)

    # 4. Emit
    state = emit_diagram_state(package, edges, root_label=root_label)

    # 5. Optional schema validation
    if validate:
        import json as _json

        import jsonschema

        from layup_python._schema_path import SCHEMA_PATH

        with SCHEMA_PATH.open() as f:
            schema = _json.load(f)
        jsonschema.validate(state, schema)

    return state


def parse_package_to_file(
    path: str | Path,
    output: str | Path,
    *,
    root_label: str | None = None,
    ignore: frozenset[str] | None = None,
    validate: bool = True,
    indent: int = 2,
) -> None:
    """Parse a Python package and write the result as JSON to *output*.

    Parameters
    ----------
    path:
        Root directory of the Python package.
    output:
        Destination file path.  Parent directories are created if needed.
    root_label:
        Optional label for the root diagram.
    ignore:
        Additional directory names to exclude during walking.
    validate:
        Validate the output against the bundled JSON Schema (default: True).
    indent:
        JSON indentation level (default: 2).
    """
    state = parse_package(path, root_label=root_label, ignore=ignore, validate=validate)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=indent)
