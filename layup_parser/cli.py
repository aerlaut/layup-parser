"""Command-line interface for layup-python.

Usage
-----
::

    layup-parse <path> [OPTIONS]

    Options:
      -o, --output FILE          Write JSON to FILE (default: stdout)
      --lang TEXT                Source language (default: python)
      --root-label TEXT          Label for the root diagram (default: package name)
      --validate / --no-validate Validate against schema before output (default: on)
      --indent INTEGER           JSON indentation level (default: 2)
      --ignore TEXT              Extra directory names to skip (repeatable)
      --help                     Show this message and exit.

Examples
--------
::

    # Print to stdout
    layup-parse ./mypkg

    # Write to file
    layup-parse ./mypkg -o diagram.json

    # Custom root label, skip a directory, no validation
    layup-parse ./mypkg --root-label "My Service" --ignore tests --no-validate
"""

from __future__ import annotations

import json
import sys

import click

from layup_parser import parse_package
from layup_parser.parser import SUPPORTED_LANGUAGES


@click.command(name="layup-parse")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "-o",
    "--output",
    "output_file",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write JSON to this file (default: stdout).",
)
@click.option(
    "--lang",
    default="python",
    show_default=True,
    type=click.Choice(SUPPORTED_LANGUAGES, case_sensitive=False),
    help="Source language of the package to parse.",
)
@click.option(
    "--root-label",
    default=None,
    show_default=True,
    help="Label for the root component diagram (default: package directory name).",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    show_default=True,
    help="Validate output against the bundled JSON Schema.",
)
@click.option(
    "--indent",
    default=2,
    show_default=True,
    type=int,
    help="JSON indentation level.",
)
@click.option(
    "--ignore",
    "ignore_dirs",
    multiple=True,
    metavar="DIR",
    help="Extra directory names to skip (repeatable, e.g. --ignore tests --ignore docs).",
)
def main(
    path: str,
    output_file: str | None,
    lang: str,
    root_label: str | None,
    validate: bool,
    indent: int,
    ignore_dirs: tuple[str, ...],
) -> None:
    """Parse a source package at PATH and emit a Layup DiagramState JSON.

    Cross-module inheritance edges are not rendered in the output (v1
    limitation) but are reported as warnings on stderr.
    """
    ignore: frozenset[str] | None = frozenset(ignore_dirs) if ignore_dirs else None

    try:
        state = parse_package(
            path,
            lang=lang,
            root_label=root_label,
            ignore=ignore,
            validate=validate,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # pragma: no cover
        click.echo(f"Unexpected error: {exc}", err=True)
        sys.exit(2)

    json_output = json.dumps(state, indent=indent)

    if output_file:
        from pathlib import Path

        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_output, encoding="utf-8")
        click.echo(f"Written to {out}", err=True)
    else:
        click.echo(json_output)
