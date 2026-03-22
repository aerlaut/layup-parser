# Task 1: Remove cross-module inheritance filter

## Motivation

The relationship resolver already produces cross-module `InheritanceEdge` objects and marks them `cross_module=True`. They were historically suppressed in the emitter as a deliberate design choice, but the decision has been revisited: cross-module inheritance is meaningful and should appear in the output diagram.

## Changes

### `layup_parser/emitter/layup.py`
- Remove the `if not edge.cross_module` guard (line ~244)
- Rename `same_module_edges_by_mod` and related variables — they no longer need the "same module" grouping constraint
- Ensure all edges (regardless of `cross_module`) are passed into `_build_code_level` and serialised into `all_edges`
- Note: layout (`layout_classes`) can continue to receive only same-module edges per module — cross-module edges still render correctly since both endpoint nodes exist in the unified code level

### `layup_parser/relationships.py`
- Update warning string: remove `"(not rendered)"` from the cross-module warning message (they are now rendered)

### `docs/ARCHITECTURE.md`
- Remove the invariant: *"Cross-module inheritance edges are never rendered."*
- Replace with a note that `cross_module` is an informational flag on `InheritanceEdge` and that all resolved edges are rendered

### Tests
- `tests/test_relationships.py` — update expected warning strings
- `tests/test_emitter.py` — assert cross-module edges now appear in the code-level output edges
