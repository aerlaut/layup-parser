# Task 2: Rewrite Emitter for New `DiagramState` Schema (v2)

## Motivation

The new schema (v2) fundamentally changes the `DiagramState` shape. The old
emitter produces a `diagrams` map (arbitrary ids → DiagramLevel) with a
`rootId` / `navigationStack` for drill-down navigation. The new schema instead
uses four **fixed** level keys (`context`, `container`, `component`, `code`)
under a `levels` object, and nodes reference their parent at the level above
via an optional `parentNodeId` field.

The Python UML emitter must be rewritten to produce the new structure:

- **`component` level** — one `component` node per module (same content as the
  old root diagram, minus `childDiagramId`).
- **`code` level** — one UML node per class, each carrying `parentNodeId`
  set to its owning module's id (linking it to the component-level node).
  Inheritance edges remain at the code level; cross-module edges are still
  suppressed.
- **`context` and `container` levels** — always emitted as empty levels.

### Old top-level structure

```json
{
  "version": 1,
  "rootId": "root",
  "navigationStack": ["root"],
  "selectedId": null,
  "pendingNodeType": null,
  "diagrams": {
    "root":          { "id": "root", "level": "component", "label": "mypkg", ... },
    "mypkg__utils":  { "id": "mypkg__utils", "level": "code", "label": "mypkg.utils", ... }
  }
}
```

### New top-level structure

```json
{
  "version": 2,
  "currentLevel": "component",
  "selectedId": null,
  "pendingNodeType": null,
  "levels": {
    "context":   { "level": "context",   "nodes": [], "edges": [], "annotations": [] },
    "container": { "level": "container", "nodes": [], "edges": [], "annotations": [] },
    "component": { "level": "component", "nodes": [<module nodes>], "edges": [], "annotations": [] },
    "code":      { "level": "code",      "nodes": [<class nodes with parentNodeId>], "edges": [<inheritance edges>], "annotations": [] }
  }
}
```

## Files to change

### `layup_python/emitter/layup.py`

1. **Remove** `ROOT_DIAGRAM_ID` constant (no longer needed).
2. **Update module-string docstring** to describe the new structure.
3. **`_serialise_class_node`** — remove `child_diagram_id` parameter and
   `childDiagramId` output; accept `parent_node_id: str | None` and include
   `parentNodeId` when set.
4. **`_serialise_module_node`** — remove `childDiagramId`; keep other fields.
5. **`_build_component_level`** (rename from `_build_root_diagram`) — returns a
   level dict with key `"component"` and no `id`/`label` fields.
6. **`_build_code_level`** (replaces per-module `_build_module_diagram`) —
   iterates over *all* modules, collects all class nodes (each with
   `parentNodeId = cls.module_id`) and all same-module edges into a single
   `code` level dict.
7. **`emit_diagram_state`** — assemble the new top-level dict:
   - Remove `rootId`, `navigationStack`.
   - Add `currentLevel: "component"`.
   - Replace `diagrams` with `levels` containing the four fixed keys.
   - Layout calls remain unchanged (module positions for component level;
     per-module class positions for code level).

### Layout note

`layout_classes` is called once per module (same as before) to get class
positions. All per-module positions are merged into a single dict for the
unified code level — no structural change to the layout module needed.

## Acceptance criteria

- `emit_diagram_state` returns a dict with `levels` (not `diagrams`).
- `levels` always contains exactly the four keys: `context`, `container`,
  `component`, `code`.
- Module nodes appear under `levels["component"]["nodes"]`.
- Class nodes appear under `levels["code"]["nodes"]`, each with
  `parentNodeId` equal to their module's id.
- Inheritance edges appear under `levels["code"]["edges"]`.
- Cross-module edges are not present in any level.
- `currentLevel` is `"component"`.
- `rootId` and `navigationStack` keys are **absent**.
- `jsonschema.validate(result, schema)` passes for all existing fixture-based
  tests.
