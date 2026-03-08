# Task 1: Update Schema Version and Add `NodeType.RECORD`

## Motivation

The upstream `diagram.schema.json` has been updated to version **2**. Two
small changes in the Python library need to mirror that immediately:

1. The `SCHEMA_VERSION` constant (used by the emitter and tests) must change
   from `1` to `2` so that every emitted `DiagramState` carries the correct
   `version` field.
2. The new schema adds `"record"` to `C4NodeType` (alongside `class`,
   `abstract-class`, `interface`, `enum`). The `NodeType` enum in `models.py`
   should expose this value so that parsers and tests can reference it, and so
   that `test_all_node_types_validate` continues to exercise every supported
   node type.

## Files to change

### `layup_python/_schema_path.py`

```python
SCHEMA_VERSION = 2   # was 1
```

### `layup_python/models.py` — `NodeType` enum

Add the new member:

```python
class NodeType(str, Enum):
    CLASS          = "class"
    ABSTRACT_CLASS = "abstract-class"
    INTERFACE      = "interface"
    ENUM           = "enum"
    RECORD         = "record"   # ← add this
```

Also update the docstring to mention `record`.

## Acceptance criteria

- `SCHEMA_VERSION` equals `2`.
- `NodeType.RECORD.value == "record"`.
- Existing unit tests in `test_models.py` still pass.
