"""Internal intermediate representation (IR) dataclasses.

These are the data structures that flow between the parser, relationship
resolver, layout engine, and emitter.  They are deliberately simple
(stdlib dataclasses only — no third-party deps) so the parser layer stays
lightweight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MemberKind(str, Enum):
    ATTRIBUTE = "attribute"
    OPERATION = "operation"


class MemberVisibility(str, Enum):
    PUBLIC = "+"
    PRIVATE = "-"
    PROTECTED = "#"
    PACKAGE = "~"


class NodeType(str, Enum):
    """Subset of Layup C4NodeType values used by the Python UML layer."""

    CLASS = "class"
    ABSTRACT_CLASS = "abstract-class"
    INTERFACE = "interface"
    ENUM = "enum"
    RECORD = "record"


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@dataclass
class ParsedMember:
    """A single attribute or operation on a class."""

    id: str
    kind: MemberKind
    visibility: MemberVisibility
    name: str

    # Optional enrichment
    type_: str | None = None
    """Field type for attributes; return type for operations."""

    params: str | None = None
    """Parameter list string for operations, e.g. ``(x: int, y: str)``."""

    is_static: bool = False
    is_abstract: bool = False


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


@dataclass
class ParsedClass:
    """A parsed Python class / enum / Protocol."""

    id: str
    """Stable unique identifier, e.g. ``<module_id>.<ClassName>``."""

    name: str
    """Simple class name."""

    module_id: str
    """ID of the owning :class:`ParsedModule`."""

    node_type: NodeType = NodeType.CLASS

    members: list[ParsedMember] = field(default_factory=list)

    bases: list[str] = field(default_factory=list)
    """Raw base-class name strings as they appear in source (not resolved)."""


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------


@dataclass
class ParsedModule:
    """A single ``.py`` file within the package tree."""

    id: str
    """Stable unique identifier derived from the dotted module path."""

    name: str
    """Dotted module path, e.g. ``mypkg.utils`` or ``mypkg.__init__``."""

    file_path: str
    """Absolute path to the ``.py`` file."""

    description: str | None = None
    """Short description of the module, typically extracted from its docstring."""

    classes: list[ParsedClass] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Package
# ---------------------------------------------------------------------------


@dataclass
class ParsedPackage:
    """The top-level result of walking a Python package directory."""

    name: str
    """Root package name (the directory name)."""

    root_path: str
    """Absolute path to the root directory."""

    modules: list[ParsedModule] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


@dataclass
class InheritanceEdge:
    """A resolved inheritance relationship between two parsed classes."""

    id: str
    """Stable unique identifier for this edge."""

    source_id: str
    """ID of the *derived* (child) :class:`ParsedClass`."""

    target_id: str
    """ID of the *base* (parent) :class:`ParsedClass`."""

    cross_module: bool = False
    """True when source and target belong to different modules."""


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
