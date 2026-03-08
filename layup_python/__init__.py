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
from layup_python.parser import get_parser
from layup_python.relationships import resolve_inheritance

__all__ = ["parse_package", "parse_package_to_file"]


def parse_package(
    path: str | Path,
    *,
    lang: str = "python",
    root_label: str | None = None,
    ignore: frozenset[str] | None = None,
    validate: bool = True,
) -> dict:
    """Parse a source package and return a Layup ``DiagramState`` dict.

    Parameters
    ----------
    path:
        Root directory of the source package.  For Python this must contain
        ``__init__.py``; requirements vary per language.
    lang:
        Language identifier for the parser to use (default: ``"python"``).
        See :data:`~layup_python.parser.SUPPORTED_LANGUAGES` for available
        options.
    root_label:
        Optional label for the root component diagram.  Defaults to the
        package directory name.
    ignore:
        Additional directory names to exclude during walking (merged with the
        built-in exclusion list defined by each language parser).
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
        If *path* is not a valid source package directory, or *lang* is not
        a supported language identifier.
    jsonschema.ValidationError
        If *validate* is ``True`` and the output does not match the schema
        (should never happen — indicates a bug in the emitter).
    """
    # 1. Walk + extract via the language-specific parser
    parser = get_parser(lang)
    package: ParsedPackage = parser.parse(Path(path), ignore=ignore)

    # 2. Resolve relationships
    edges, warnings = resolve_inheritance(package)

    # Emit warnings to stderr so stdout stays clean for piping
    for w in warnings:
        print(f"[layup-python] WARNING: {w}", file=sys.stderr)

    # 3. Emit
    state = emit_diagram_state(package, edges, root_label=root_label)

    # 4. Optional schema validation
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
    lang: str = "python",
    root_label: str | None = None,
    ignore: frozenset[str] | None = None,
    validate: bool = True,
    indent: int = 2,
) -> None:
    """Parse a source package and write the result as JSON to *output*.

    Parameters
    ----------
    path:
        Root directory of the source package.
    output:
        Destination file path.  Parent directories are created if needed.
    lang:
        Language identifier for the parser to use (default: ``"python"``).
    root_label:
        Optional label for the root diagram.
    ignore:
        Additional directory names to exclude during walking.
    validate:
        Validate the output against the bundled JSON Schema (default: True).
    indent:
        JSON indentation level (default: 2).
    """
    state = parse_package(path, lang=lang, root_label=root_label, ignore=ignore, validate=validate)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=indent)
