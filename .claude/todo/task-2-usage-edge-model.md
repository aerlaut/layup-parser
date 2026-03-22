# Task 2: Add `UsageEdge` model to IR

## Motivation

To derive class-level usage (dependency) relationships at the resolver layer, a typed model object is needed — consistent with how `InheritanceEdge` represents inheritance. Keeping `UsageEdge` separate from `InheritanceEdge` preserves semantic clarity and lets the emitter render them differently (dashed + open-arrow vs. solid + hollow-triangle).

This task is a prerequisite for Task 3 (usage resolver) and Task 4 (emitter wiring).

## Changes

### `layup_parser/models.py`
Add a new dataclass in the Relationships section:

```python
@dataclass
class UsageEdge:
    """A resolved usage (dependency) relationship between two parsed classes.

    A usage edge A → B means class A references class B in a type annotation
    (attribute type, operation return type, or parameter type).
    """

    id: str
    """Stable unique identifier for this edge."""

    source_id: str
    """ID of the class that uses (depends on) the target."""

    target_id: str
    """ID of the class being used."""

    cross_module: bool = False
    """True when source and target belong to different modules."""
```

Also export `UsageEdge` from `__all__` if the models module has one.
