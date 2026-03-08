"""Recursive Python package/module discovery.

Given a root directory, the walker:
1. Verifies it is a Python package (contains ``__init__.py``).
2. Recursively collects all ``.py`` files, skipping common non-source
   directories (``__pycache__``, virtual-envs, build artefacts, etc.).
3. Returns a :class:`~layup_python.models.ParsedPackage` whose modules are
   populated with file paths and dotted names but *no* classes yet — class
   extraction is performed separately by the extractor.
"""

from __future__ import annotations

import re
from pathlib import Path

from layup_python.models import ParsedModule, ParsedPackage

# Directories to skip unconditionally
_DEFAULT_IGNORE: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        "venv",
        "env",
        ".env",
        "site-packages",
        "dist",
        "build",
        "dist-info",
        "egg-info",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)


def _is_package(directory: Path) -> bool:
    """Return True if *directory* contains an ``__init__.py`` file."""
    return (directory / "__init__.py").is_file()


def _module_id(dotted_name: str) -> str:
    """Convert a dotted module name to a stable ID string.

    Replaces dots with double-underscores so the result is usable as a
    JSON key / diagram ID without confusion.
    Example: ``mypkg.utils`` → ``mypkg__utils``
    """
    return dotted_name.replace(".", "__")


def _collect_modules(
    directory: Path,
    package_prefix: str,
    ignore: frozenset[str],
) -> list[ParsedModule]:
    """Recursively collect :class:`ParsedModule` objects under *directory*.

    Parameters
    ----------
    directory:
        The directory to walk (must itself be a Python package).
    package_prefix:
        The dotted module prefix for this directory, e.g. ``"mypkg"`` or
        ``"mypkg.sub"``.
    ignore:
        Set of directory-name patterns to skip.
    """
    modules: list[ParsedModule] = []

    for entry in sorted(directory.iterdir()):
        if entry.name in ignore:
            continue

        if entry.is_dir():
            if _is_package(entry):
                sub_prefix = f"{package_prefix}.{entry.name}"
                # Recurse into sub-package
                modules.extend(_collect_modules(entry, sub_prefix, ignore))
        elif entry.is_file() and entry.suffix == ".py":
            stem = entry.stem  # e.g. "utils" or "__init__"
            dotted_name = (
                f"{package_prefix}.{stem}" if stem != "__init__" else package_prefix
            )
            mod_id = _module_id(dotted_name)
            modules.append(
                ParsedModule(
                    id=mod_id,
                    name=dotted_name,
                    file_path=str(entry.resolve()),
                )
            )

    return modules


def walk_package(
    root: str | Path,
    *,
    ignore: frozenset[str] | None = None,
) -> ParsedPackage:
    """Walk a Python package rooted at *root* and return a :class:`ParsedPackage`.

    Parameters
    ----------
    root:
        Path to the root of the Python package (a directory containing
        ``__init__.py``).
    ignore:
        Extra directory names to exclude in addition to the built-in list.
        Pass an empty frozenset to use *only* the built-in list.

    Raises
    ------
    ValueError
        If *root* does not exist or is not a Python package directory.
    """
    root = Path(root).resolve()

    if not root.is_dir():
        raise ValueError(f"Root path is not a directory: {root}")
    if not _is_package(root):
        raise ValueError(
            f"Root directory is not a Python package (no __init__.py found): {root}"
        )

    effective_ignore = _DEFAULT_IGNORE | (ignore or frozenset())

    package_name = root.name
    modules = _collect_modules(root, package_name, effective_ignore)

    return ParsedPackage(
        name=package_name,
        root_path=str(root),
        modules=modules,
    )
