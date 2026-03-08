"""Parser package — language-aware parser registry.

Use :func:`get_parser` to retrieve a
:class:`~layup_parser.parser.base.LanguageParser` for a specific language,
then call its :meth:`~layup_parser.parser.base.LanguageParser.parse` method
to obtain a fully-populated :class:`~layup_parser.models.ParsedPackage`.

Supported languages
-------------------
- ``"python"``  — via :class:`~layup_parser.parser.python.PythonParser`

Adding a new language
---------------------
1. Create ``layup_parser/parser/<lang>/`` with a class implementing the
   :class:`~layup_parser.parser.base.LanguageParser` protocol.
2. Add an entry to :data:`_PARSERS` below.
"""

from __future__ import annotations

from layup_parser.parser.base import LanguageParser
from layup_parser.parser.python import PythonParser

# Registry: language identifier → parser class (instantiated on demand).
# Add new language parsers here as they are implemented.
_PARSERS: dict[str, type] = {
    "python": PythonParser,
}

#: Tuple of language identifiers that are currently supported.
SUPPORTED_LANGUAGES: tuple[str, ...] = tuple(sorted(_PARSERS))


def get_parser(lang: str) -> LanguageParser:
    """Return a :class:`~layup_parser.parser.base.LanguageParser` instance for *lang*.

    Parameters
    ----------
    lang:
        Language identifier string, e.g. ``"python"``.

    Returns
    -------
    LanguageParser
        A ready-to-use parser instance.

    Raises
    ------
    ValueError
        If *lang* is not in :data:`SUPPORTED_LANGUAGES`.
    """
    cls = _PARSERS.get(lang)
    if cls is None:
        supported = ", ".join(f'"{s}"' for s in SUPPORTED_LANGUAGES)
        raise ValueError(
            f"Unsupported language: {lang!r}. Supported languages: {supported}"
        )
    return cls()


__all__ = ["LanguageParser", "SUPPORTED_LANGUAGES", "get_parser"]
