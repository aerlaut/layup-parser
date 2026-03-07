# Layup Diagram Schema

This directory contains the JSON Schema for the **`DiagramState`** format — the file format used by layup's JSON import/export.

## Files

- **`diagram.schema.json`** — [JSON Schema (draft-07)](https://json-schema.org/specification-links.html#draft-7) describing a valid `DiagramState` object.

## Usage

External tools that produce layup-compatible JSON files should validate their output against this schema. For example, in Python with `jsonschema`:

```python
import json
import jsonschema

with open("diagram.schema.json") as f:
    schema = json.load(f)

with open("my_output.json") as f:
    diagram = json.load(f)

jsonschema.validate(diagram, schema)
```

## Schema version

The `version` field in a `DiagramState` must match the schema version supported by the application. The current version is **`1`** (defined in `src/utils/constants.ts` as `SCHEMA_VERSION`).

## Regenerating the schema

The schema is auto-generated from the TypeScript types in `src/types.ts`. To regenerate after type changes:

```bash
npm run schema
```

This runs `ts-json-schema-generator` targeting the `DiagramState` type and writes the output to `schema/diagram.schema.json`.

## Producing a valid `DiagramState` from external tools

When generating a diagram file programmatically (e.g. from a Python package parser), use these defaults for UI-state fields:

| Field              | Value                        | Notes                                                |
|--------------------|------------------------------|------------------------------------------------------|
| `version`          | `1`                          | Must match the app's `SCHEMA_VERSION`                |
| `rootId`           | ID of your root diagram      | Typically `"root"`                                   |
| `navigationStack`  | `["<rootId>"]`               | Single-element array pointing to the root diagram    |
| `selectedId`       | `null`                       | No selection on open                                 |
| `pendingNodeType`  | `null`                       | No pending placement                                 |

### Key types

- **`DiagramLevel`** — A single diagram canvas. Has a `level` (`"context"`, `"container"`, `"component"`, or `"code"`), plus arrays of `nodes`, `edges`, and `annotations`.
- **`C4Node`** — A node on the canvas. Required fields: `id`, `type`, `label`, `position`. For UML code-level nodes (`class`, `abstract-class`, `interface`, `enum`, `record`), populate `members` with `ClassMember` objects. For ERD nodes (`erd-table`, `erd-view`), populate `columns` with `TableColumn` objects.
- **`C4Edge`** — A connection between two nodes. Required fields: `id`, `source`, `target`. Use `markerEnd` to set arrow style (e.g. `"hollow-triangle"` for inheritance, `"filled-diamond"` for composition).
- **`ClassMember`** — An attribute or operation on a UML class node. Required fields: `id`, `kind`, `visibility`, `name`.
- **`MemberVisibility`** — `"+"` (public), `"-"` (private), `"#"` (protected), `"~"` (package).

### Drill-down hierarchy

Nodes can link to child diagrams via `childDiagramId`. The `diagrams` map is flat — all diagram levels are stored at the top level keyed by ID. The hierarchy is implicit through `childDiagramId` references. For a Python UML parser, a typical structure would be:

```
root (code level)
├── nodes: [class, enum, interface, ...]
└── edges: [inheritance, composition, ...]
```

Or, for a multi-module package:

```
root (component level)
├── nodes: [module_a (childDiagramId → diag_a), module_b (childDiagramId → diag_b)]
└── edges: [module_a → module_b]

diag_a (code level)
├── nodes: [ClassA, ClassB]
└── edges: [ClassA → ClassB]

diag_b (code level)
├── nodes: [ClassC]
└── edges: []
```
