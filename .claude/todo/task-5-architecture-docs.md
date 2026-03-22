# Task 5: Update ARCHITECTURE.md

## Motivation

The architecture document has an explicit invariant stating cross-module edges are never rendered, and it doesn't mention `UsageEdge` or the usage resolver. After Tasks 1–4 are complete, the document needs to reflect the new state.

Depends on: **Task 1**, **Task 2**, **Task 3**, **Task 4** (do last).

## Changes

### `docs/ARCHITECTURE.md`

**Directory layout** — add new entry:
```
layup_parser/
  usage.py   # Resolves type annotation strings into UsageEdge objects
```

**Core data model** — add `UsageEdge` alongside `InheritanceEdge`:
```
UsageEdge                               (resolved after walking)
  ├── source_id → dependent ParsedClass.id
  ├── target_id → used ParsedClass.id
  └── cross_module: bool
```

**Data flow** — add `resolve_usage` step:
```
resolve_inheritance(package)  # raw base names → InheritanceEdge list
resolve_usage(package)        # type annotations → UsageEdge list
    ↓
emit_diagram_state(...)       # IR + edges → DiagramState dict
```

**Invariants / Constraints** — update:
- Remove: *"Cross-module inheritance edges are never rendered."*
- Add: *"`cross_module` is an informational flag on both `InheritanceEdge` and `UsageEdge`. All resolved edges are rendered regardless of module boundary."*
- Add: *"Usage edges are derived from static type annotations only (attribute types, return types, parameter types). Runtime instantiation and method-call analysis is out of scope."*
