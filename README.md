# layup-python

A Python package importer for [Layup](https://github.com/aerlaut/layup) — parses a Python package's structure and exports it as a Layup `DiagramState` JSON, ready to be imported into Layup for diagramming.

---

## Installation

Requires Python 3.10+.

```bash
pip install layup-python
```

Or install from source:

```bash
git clone https://github.com/aerlaut/layup-python.git
cd layup-python
pip install .
```

---

## Usage

### CLI

After installation, the `layup-parse` command is available:

```bash
# Print diagram JSON to stdout
layup-parse ./mypkg

# Write diagram JSON to a file
layup-parse ./mypkg -o diagram.json

# Custom root label, skip a directory, disable validation
layup-parse ./mypkg --root-label "My Service" --ignore tests --no-validate
```

**Options:**

| Option | Description | Default |
|---|---|---|
| `-o, --output FILE` | Write JSON to a file instead of stdout | stdout |
| `--root-label TEXT` | Label for the root diagram | Package directory name |
| `--validate / --no-validate` | Validate output against bundled JSON Schema | `--validate` |
| `--indent INTEGER` | JSON indentation level | `2` |
| `--ignore DIR` | Extra directory names to skip (repeatable) | — |

### Python API

```python
from layup_python import parse_package, parse_package_to_file

# Returns a DiagramState dict
diagram = parse_package("/path/to/mypkg")

# Convenience: write JSON directly to a file
parse_package_to_file("/path/to/mypkg", "diagram.json")
```

`parse_package` accepts the following keyword arguments:

- `root_label` — optional label for the root component diagram
- `ignore` — `frozenset` of directory names to exclude during walking
- `validate` — validate output against the bundled JSON Schema (default: `True`)

---

## How it works

`layup-python` walks a Python package directory, extracts classes, functions, and their relationships (e.g. inheritance), and emits a structured `DiagramState` JSON that can be imported directly into [Layup](https://github.com/aerlaut/layup).

---

## License

MIT
