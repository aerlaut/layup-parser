# Task 4: Wire usage edges into pipeline and emitter

## Motivation

With `UsageEdge` objects produced by the resolver (Task 3), the pipeline and emitter need to be updated to accept, pass through, and serialise them into the DiagramState JSON output at the code level.

Depends on: **Task 1**, **Task 2**, **Task 3**.

## Changes

### `layup_parser/__init__.py`
- Call `resolve_usage(package)` after `resolve_inheritance`
- Pass `usage_edges` to `emit_diagram_state`
- Emit any usage warnings to stderr (same pattern as inheritance warnings)

```python
from layup_parser.usage import resolve_usage

edges, warnings = resolve_inheritance(package)
usage_edges, usage_warnings = resolve_usage(package)

for w in warnings + usage_warnings:
    print(f"[layup-parser] WARNING: {w}", file=sys.stderr)

state = emit_diagram_state(package, edges, usage_edges=usage_edges, ...)
```

### `layup_parser/emitter/layup.py`
- Add `usage_edges: list[UsageEdge] = ()` parameter to `emit_diagram_state`
- Add `_serialise_usage_edge(edge: UsageEdge) -> dict`:
  ```python
  {
      "id": edge.id,
      "source": edge.source_id,
      "target": edge.target_id,
      "lineStyle": "dashed",
      "markerEnd": "open-arrow",
  }
  ```
- In `_build_code_level`, append serialised usage edges into `all_edges` alongside inheritance edges
- Update imports: add `UsageEdge` from `layup_parser.models`

### Tests
- `tests/test_emitter.py` — assert usage edges appear in code-level output with correct `lineStyle` and `markerEnd`
- `tests/test_api.py` — integration test: parse a package with known usage relationships, assert edges present in output
