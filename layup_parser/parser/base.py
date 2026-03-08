"""Language-agnostic parser protocol.

Any language parser must implement :class:`LanguageParser` so that it can be
used as a drop-in backend for :func:`layup_parser.parse_package`.

Adding a new language
---------------------
1. Create a sub-package under ``layup_parser/parser/<lang>/``.
2. Implement a class that satisfies this protocol (a concrete class or a
   :class:`typing.Protocol` structural match both work).
3. Register it in :data:`layup_parser.parser._PARSERS` under a stable
   language-identifier string.

The downstream pipeline — relationship resolution, layout, and emission — is
entirely language-agnostic and requires no changes when a new language is
added.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from layup_parser.models import ParsedPackage


@runtime_checkable
class LanguageParser(Protocol):
    """Protocol for language-specific source-tree walkers and extractors.

    Implementations must walk the source tree rooted at *root*, extract
    structural information (classes, members, inheritance bases) from each
    source file, and return a fully-populated
    :class:`~layup_parser.models.ParsedPackage` with all
    :class:`~layup_parser.models.ParsedModule` objects fully populated.

    The downstream pipeline (relationship resolution, layout, emission) is
    language-agnostic and does not need to be re-implemented per language.
    """

    def parse(
        self,
        root: Path,
        *,
        ignore: frozenset[str] | None = None,
    ) -> ParsedPackage:
        """Walk *root* and extract all classes, returning a fully-populated package.

        Parameters
        ----------
        root:
            Absolute path to the root of the source tree.
        ignore:
            Additional directory names to skip (merged with any built-in
            exclusions defined by each implementation).

        Returns
        -------
        ParsedPackage
            A package object whose modules are all populated with extracted
            classes and members.

        Raises
        ------
        ValueError
            If *root* is not a valid source tree for the target language.
        """
        ...
