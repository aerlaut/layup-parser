# Task 3: Add `usage.py` resolver

## Motivation

Usage (dependency) edges between classes should be derived at the resolver layer — not inside the emitter — so they are available as typed model objects to any future emitter (Mermaid, PlantUML, etc.) and can be tested independently of JSON shape. This follows the existing pattern established by `relationships.py` for inheritance.

Depends on: **Task 2** (UsageEdge model must exist first).

## Changes

### New file: `layup_parser/usage.py`

Create `resolve_usage(package: ParsedPackage) -> tuple[list[UsageEdge], list[str]]`.

**Derivation strategy:**
1. Build a `name → ParsedClass` lookup across all modules (same approach as `resolve_inheritance`)
2. For each class in the package, collect all type annotation strings from its members:
   - `ParsedMember.type_` (attribute types and operation return types)
   - `ParsedMember.params` string (scan for known class names within the params string)
3. For each type name found that resolves to a known class:
   - Skip if it resolves to the class itself (no self-loops)
   - Skip duplicates — emit at most one `UsageEdge` per (source_id, target_id) pair
   - Set `cross_module=True` if source and target are in different modules
4. Return `(edges, warnings)` — warnings can note cross-module usage if useful

**Edge ID scheme:** `usage_1`, `usage_2`, … (prefix distinguishes from `edge_N` inheritance IDs)

**Scope note:** This is purely annotation-based (static). It does not analyse function bodies for instantiation or method calls — that is a more invasive analysis and can be added later.

### Tests
- `tests/test_usage.py` — new test file
- Test same-module usage (class A has attribute of type B → edge A→B)
- Test cross-module usage
- Test deduplication (multiple members referencing same class → one edge)
- Test self-reference exclusion
- Test unresolvable type names are silently dropped
- Extend fixture `tests/fixtures/sample_pkg/` if needed to cover cross-module annotation references
