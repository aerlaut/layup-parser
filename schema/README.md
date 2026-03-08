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

The `version` field in a `DiagramState` must match the schema version supported by the application. The current version is **`2`** (defined in `src/utils/constants.ts` as `SCHEMA_VERSION`).

## Regenerating the schema

The schema is auto-generated from the TypeScript types in `src/types.ts`. To regenerate after type changes:

```bash
npm run schema
```

This runs `ts-json-schema-generator` targeting the `DiagramState` type and writes the output to `schema/diagram.schema.json`.

## Producing a valid `DiagramState` from external tools

When generating a diagram file programmatically (e.g. from a Python package parser), use these defaults for UI-state fields:

| Field             | Value             | Notes                                                |
|-------------------|-------------------|------------------------------------------------------|
| `version`         | `2`               | Must match the app's `SCHEMA_VERSION`                |
| `currentLevel`    | `"context"`       | The level shown when the diagram is first opened     |
| `selectedId`      | `null`            | No selection on open                                 |
| `pendingNodeType` | `null`            | No pending placement                                 |

### Top-level structure

A `DiagramState` has four fixed levels, always present, keyed by `C4LevelType`:

```json
{
  "version": 2,
  "currentLevel": "context",
  "selectedId": null,
  "pendingNodeType": null,
  "levels": {
    "context":   { "level": "context",   "nodes": [], "edges": [], "annotations": [] },
    "container": { "level": "container", "nodes": [], "edges": [], "annotations": [] },
    "component": { "level": "component", "nodes": [], "edges": [], "annotations": [] },
    "code":      { "level": "code",      "nodes": [], "edges": [], "annotations": [] }
  }
}
```

All four level keys (`context`, `container`, `component`, `code`) are required even if empty.

### Key types

- **`DiagramLevel`** — A single diagram canvas. Has a `level` (`"context"`, `"container"`, `"component"`, or `"code"`), plus arrays of `nodes`, `edges`, and `annotations`.
- **`C4Node`** — A node on the canvas. Required fields: `id`, `type`, `label`, `position`. For UML code-level nodes (`class`, `abstract-class`, `interface`, `enum`, `record`), populate `members` with `ClassMember` objects. For ERD nodes (`erd-table`, `erd-view`), populate `columns` with `TableColumn` objects.
- **`C4Edge`** — A connection between two nodes. Required fields: `id`, `source`, `target`. Use `markerEnd` to set arrow style (e.g. `"hollow-triangle"` for inheritance, `"filled-diamond"` for composition).
- **`Annotation`** — A free-floating canvas element (sticky note, group box, package). Required fields: `id`, `type`, `label`, `position`. Never participates in C4 hierarchy.
- **`ClassMember`** — An attribute or operation on a UML class node. Required fields: `id`, `kind`, `visibility`, `name`.
- **`MemberVisibility`** — `"+"` (public), `"-"` (private), `"#"` (protected), `"~"` (package).

### C4 level hierarchy and `parentNodeId`

The four levels form a fixed top-down hierarchy:

```
context → container → component → code
```

Nodes at each level (except `context`) can reference a node at the level above via the optional `parentNodeId` field. This is how layup groups containers under a system, components under a container, and so on. Nodes without a `parentNodeId` are treated as top-level within their canvas.

Example: a `container` node belonging to a `system` node at the context level:

```json
{
  "id": "svc-api",
  "type": "container",
  "label": "API Service",
  "position": { "x": 100, "y": 200 },
  "parentNodeId": "sys-backend"
}
```

For a Python UML parser targeting the code level, a typical flat structure would be:

```json
{
  "levels": {
    "code": {
      "level": "code",
      "nodes": [
        { "id": "cls-a", "type": "class",     "label": "ClassA", "position": { "x": 0,   "y": 0   }, "members": [] },
        { "id": "cls-b", "type": "interface", "label": "IFoo",   "position": { "x": 300, "y": 0   }, "members": [] }
      ],
      "edges": [
        { "id": "e1", "source": "cls-a", "target": "cls-b", "markerEnd": "hollow-triangle" }
      ],
      "annotations": []
    },
    "context":   { "level": "context",   "nodes": [], "edges": [], "annotations": [] },
    "container": { "level": "container", "nodes": [], "edges": [], "annotations": [] },
    "component": { "level": "component", "nodes": [], "edges": [], "annotations": [] }
  }
}
```
