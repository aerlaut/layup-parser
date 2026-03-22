# layup-parser

A multi-language source importer for [Layup](https://github.com/aerlaut/layup) — parses a source package's structure and exports it as a Layup `NodeSubtreeExport` JSON, ready to be imported into Layup for diagramming.

Currently supports **Python**. The architecture is designed for additional languages to be added as parser backends (see [Adding a language](#adding-a-language)).

---

## Installation

Requires Python 3.10+.

```bash
pip install layup-parser
```

Or install from source:

```bash
git clone https://github.com/aerlaut/layup-parser.git
cd layup-parser
pip install .
```

---

## Usage

### CLI

After installation, the `layup-parse` command is available:

```bash
# Parse a Python package and print diagram JSON to stdout
layup-parse ./mypkg

# Write diagram JSON to a file
layup-parse ./mypkg -o diagram.json

# Specify the source language explicitly (default: python)
layup-parse ./mypkg --lang python -o diagram.json

# Custom root label, skip a directory, disable validation
layup-parse ./mypkg --root-label "My Service" --ignore tests --no-validate
```

**Options:**

| Option | Description | Default |
|---|---|---|
| `-o, --output FILE` | Write JSON to a file instead of stdout | stdout |
| `--lang TEXT` | Source language of the package to parse | `python` |
| `--root-label TEXT` | Label for the root diagram | Package directory name |
| `--validate / --no-validate` | Validate output against bundled JSON Schema | `--validate` |
| `--indent INTEGER` | JSON indentation level | `2` |
| `--ignore DIR` | Extra directory names to skip (repeatable) | — |

### Python API

```python
from layup_parser import parse_package, parse_package_to_file

# Returns a NodeSubtreeExport dict (defaults to lang="python")
diagram = parse_package("/path/to/mypkg")

# Specify the language explicitly
diagram = parse_package("/path/to/mypkg", lang="python")

# Convenience: write JSON directly to a file
parse_package_to_file("/path/to/mypkg", "diagram.json")
parse_package_to_file("/path/to/mypkg", "diagram.json", lang="python")
```

`parse_package` and `parse_package_to_file` accept the following keyword arguments:

| Argument | Type | Description | Default |
|---|---|---|---|
| `lang` | `str` | Language identifier for the parser backend | `"python"` |
| `root_label` | `str \| None` | Label for the root component diagram | Package directory name |
| `ignore` | `frozenset[str] \| None` | Directory names to exclude during walking | — |
| `validate` | `bool` | Validate output against the bundled JSON Schema | `True` |
| `indent` | `int` | JSON indentation level *(to-file only)* | `2` |

---

## Supported languages

| Language | Identifier | Discovery | Extraction |
|---|---|---|---|
| Python | `"python"` | `__init__.py` packages, `.py` files | stdlib `ast` module |

---

## How it works

`layup-parser` uses a four-stage pipeline that is **language-agnostic** after the first stage:

```
[LanguageParser]        [relationships]      [layout]      [emitter]
walk + extract     →    resolve edges    →   position  →   emit JSON
(language-specific)     (shared)             (shared)      (shared)
```

1. **Walk + Extract** — A `LanguageParser` backend discovers source files in the root directory and extracts classes, members, and inheritance bases into a language-agnostic intermediate representation (IR).
2. **Relationship resolution** — Inheritance base names are resolved to concrete IR nodes and tagged as same-module or cross-module edges.
3. **Layout** — Nodes are assigned positions using a hierarchical algorithm.
4. **Emission** — The IR is serialised to a Layup `NodeSubtreeExport` JSON (v1 schema).

Only stage 1 differs between languages. Stages 2–4 are shared across all backends.

---

## Adding a language

Adding a new language requires three steps: implement the parser, register it, and (optionally) write a fixture and tests.

### 1. Implement `LanguageParser`

Create a sub-package under `layup_parser/parser/<lang>/`:

```
layup_parser/parser/
└── mylang/
    ├── __init__.py
    ├── walker.py      # discovers source files, returns ParsedPackage with empty modules
    ├── extractor.py   # populates each module's .classes list
    └── parser.py      # MyLangParser: composes walker + extractor
```

`parser.py` must expose a class with a single `parse` method matching the `LanguageParser` protocol:

```python
# layup_parser/parser/mylang/parser.py
from __future__ import annotations
from pathlib import Path
from layup_parser.models import ParsedPackage

class MyLangParser:
    def parse(
        self,
        root: Path,
        *,
        ignore: frozenset[str] | None = None,
    ) -> ParsedPackage:
        # 1. Walk root to discover source files → ParsedPackage with modules
        # 2. For each module, extract classes/members → populate module.classes
        # 3. Return the fully-populated ParsedPackage
        ...
```

The IR types you need to populate are all in `layup_parser/models.py`:

| Type | Purpose |
|---|---|
| `ParsedPackage` | Top-level container (name, root path, list of modules) |
| `ParsedModule` | One source file (id, dotted name, file path, list of classes) |
| `ParsedClass` | One class/interface/enum (id, name, node type, members, base names) |
| `ParsedMember` | One attribute or method (id, kind, visibility, name, type, params) |

See `layup_parser/parser/base.py` for the full protocol docstring, and the Python implementation (`layup_parser/parser/python/`) as a reference.

### 2. Register the parser

Add one entry to `_PARSERS` in `layup_parser/parser/__init__.py`:

```python
# layup_parser/parser/__init__.py
from layup_parser.parser.mylang import MyLangParser   # add this import

_PARSERS: dict[str, type] = {
    "python": PythonParser,
    "mylang": MyLangParser,                            # add this entry
}
```

`SUPPORTED_LANGUAGES` and the CLI `--lang` choices are derived from `_PARSERS` automatically — no other changes are needed.

### 3. Add tests

Create `tests/test_<lang>_parser.py`. At minimum, mirror the structure of `tests/test_parser_registry.py` and verify that your parser:

- Returns a `ParsedPackage` with populated modules and classes.
- Propagates the `ignore` parameter correctly.
- Raises `ValueError` for an invalid root directory.

Add fixture source files under `tests/fixtures/<lang>_pkg/` to drive the tests.

---

## License

MIT
