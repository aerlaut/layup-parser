# Layup Node Subtree Schema

This directory contains the JSON Schema for the **`NodeSubtreeExport`** format — the file format used by layup's node subtree import.

## Files

- **`nodeSubtree.schema.json`** — [JSON Schema (draft-07)](https://json-schema.org/specification-links.html#draft-7) describing a valid `NodeSubtreeExport` object.

## Usage

External tools that produce layup-compatible node subtree JSON files should validate their output against this schema. For example, in Python with `jsonschema`:

```python
import json
import jsonschema

with open("nodeSubtree.schema.json") as f:
    schema = json.load(f)

with open("my_output.json") as f:
    subtree = json.load(f)

jsonschema.validate(subtree, schema)
```

## Schema version

The `version` field in a `NodeSubtreeExport` is a constant `1`. Bump it when the format changes in a breaking way.

## Top-level structure

A `NodeSubtreeExport` identifies the root C4 level and provides level data for that level and all levels below it. Levels with no content can be omitted.

```json
{
  "exportType": "node-subtree",
  "version": 1,
  "rootLevel": "component",
  "levels": {
    "component": { "level": "component", "nodes": [], "edges": [] },
    "code":      { "level": "code",      "nodes": [], "edges": [] }
  }
}
```

### Fields

| Field        | Value             | Notes                                                       |
|--------------|-------------------|-------------------------------------------------------------|
| `exportType` | `"node-subtree"`  | Constant; distinguishes this format from a full DiagramState export |
| `version`    | `1`               | Schema version; bump on breaking changes                    |
| `rootLevel`  | `C4LevelType`     | The C4 level at which the root node lives                   |
| `levels`     | object            | Level data; all four level keys are optional                |

### Level data (`NodeSubtreeLevelData`)

Each level entry has:
- `level` — the `C4LevelType` key (`"context"`, `"container"`, `"component"`, or `"code"`)
- `nodes` — array of `C4Node` objects
- `edges` — array of `C4Edge` objects

Edges at `rootLevel` are excluded (they connect to nodes outside the subtree). Edges at descendant levels are included only when both endpoints are within the subtree.

### Key types

- **`C4Node`** — A node on the canvas. Required fields: `id`, `type`, `label`, `position`. For UML code-level nodes (`class`, `abstract-class`, `interface`, `enum`, `record`), populate `members` with `ClassMember` objects.
- **`C4Edge`** — A connection between two nodes. Required fields: `id`, `source`, `target`. Use `markerEnd` to set arrow style (e.g. `"hollow-triangle"` for inheritance, `"open-arrow"` for usage/dependency).
- **`ClassMember`** — An attribute or operation on a UML class node. Required fields: `id`, `kind`, `visibility`, `name`.
- **`MemberVisibility`** — `"+"` (public), `"-"` (private), `"#"` (protected), `"~"` (package).

### Example: Python UML output

```json
{
  "exportType": "node-subtree",
  "version": 1,
  "rootLevel": "component",
  "levels": {
    "component": {
      "level": "component",
      "nodes": [
        { "id": "mypkg__utils", "type": "component", "label": "mypkg.utils", "position": { "x": 0, "y": 0 } }
      ],
      "edges": []
    },
    "code": {
      "level": "code",
      "nodes": [
        { "id": "mypkg__utils.Base",  "type": "class", "label": "Base",  "position": { "x": 0,   "y": 0   }, "parentNodeId": "mypkg__utils" },
        { "id": "mypkg__utils.Child", "type": "class", "label": "Child", "position": { "x": 300, "y": 0   }, "parentNodeId": "mypkg__utils" }
      ],
      "edges": [
        { "id": "e1", "source": "mypkg__utils.Child", "target": "mypkg__utils.Base", "markerEnd": "hollow-triangle", "lineStyle": "solid" }
      ]
    }
  }
}
```
