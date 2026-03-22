# Architecture

## Purpose

`layup-parser` walks source packages and emits a `DiagramState` JSON object consumable by the Layup diagramming tool. The output represents the package's class structure as a C4-model diagram with `component` (module) and `code` (class) levels. The tool is designed to be embedded as a library or invoked via CLI.

## Tech Stack

- **Python 3.10+**, stdlib only in the core pipeline (`ast`, `dataclasses`, `pathlib`) — keeps the parser dependency-free at runtime
- **click** — CLI argument parsing (`layup-parse` entry point)
- **jsonschema** — output validation against the bundled `schema/diagram.schema.json`; validates the emitter stays in sync with the schema, not user input

## Directory Layout

```
layup_parser/
  __init__.py          # Public API: parse_package, parse_package_to_file
  cli.py               # click CLI entry point (layup-parse command)
  models.py            # IR dataclasses: ParsedPackage → ParsedModule → ParsedClass → ParsedMember
  relationships.py     # Resolves raw base-class strings into InheritanceEdge objects
  _schema_path.py      # Resolves bundled schema path; exports SCHEMA_VERSION
  parser/
    base.py            # LanguageParser Protocol definition
    __init__.py        # Parser registry (_PARSERS dict) + get_parser()
    extractor.py       # Base extractor utilities (shared across languages)
    walker.py          # Base walker utilities (shared across languages)
    python/            # Python-specific implementation of LanguageParser
  layout/
    hierarchical.py    # Grid layout engine → Position(x, y) per node
  emitter/
    layup.py           # Converts IR + edges + positions → DiagramState dict
schema/
  diagram.schema.json  # JSON Schema for DiagramState (v2); bundled with package
docs/                  # Architecture and contributor documentation
tests/
  fixtures/            # Sample Python packages used as test inputs
```

## Core Data Model

The IR flows through the pipeline as a tree, then flattens for output:

```
ParsedPackage
  └── modules: list[ParsedModule]       (one per .py file)
        └── classes: list[ParsedClass]  (one per class/enum/Protocol)
              ├── members: list[ParsedMember]  (attributes + methods)
              └── bases: list[str]      (raw, unresolved base names)

InheritanceEdge                         (resolved after walking)
  ├── source_id → child ParsedClass.id
  ├── target_id → parent ParsedClass.id
  └── cross_module: bool
```

IDs are stable dotted-path strings (e.g., `mypkg.utils.MyClass`). They are used as node IDs in the emitted JSON.

## Data Flow

```
path + lang
    │
    ▼
get_parser(lang)              # parser registry lookup
    │
    ▼
LanguageParser.parse(root)    # walk files → extract AST → populate IR
    │                           (language-specific; only python/ exists today)
    ▼
resolve_inheritance(package)  # raw base names → InheritanceEdge list + warnings
    │
    ▼
emit_diagram_state(...)       # IR + edges → layout positions → DiagramState dict
    │
    ▼
jsonschema.validate(state)    # optional; guards against emitter regressions
    │
    ▼
DiagramState dict / JSON file
```

## Invariants / Constraints

- **Cross-module inheritance edges are never rendered.** They are resolved and returned as string warnings (printed to stderr by the CLI/API). The emitter only serialises same-module edges. This is a deliberate design choice, not an omission.
- **Base class names are dropped if unresolvable.** Stdlib, third-party, and unknown base classes produce no phantom nodes and no errors — they are silently discarded during relationship resolution.
- **IDs must be stable and globally unique** within a single parse run. The Python parser derives IDs from dotted module paths; new language parsers must guarantee the same.
- **Adding a language parser requires only two changes:** create `parser/<lang>/` implementing `LanguageParser`, and add an entry to `_PARSERS` in `parser/__init__.py`. The rest of the pipeline is language-agnostic.
- **Schema version is a single source of truth** in `_schema_path.py` (`SCHEMA_VERSION`). The emitter reads it; do not hardcode it elsewhere.
- **`root_label` is ignored by the v2 emitter** (`DiagramLevel` has no label field). The parameter exists only for call-site backwards compatibility.
