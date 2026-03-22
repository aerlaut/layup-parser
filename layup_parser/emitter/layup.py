"""Layup DiagramState JSON emitter.

Takes a fully-populated :class:`~layup_parser.models.ParsedPackage` plus
resolved :class:`~layup_parser.models.InheritanceEdge` objects and layout
positions, and returns a Python dict that validates against
``schema/diagram.schema.json``.

Output structure (v2)
---------------------
::

    DiagramState
    ├── version        → 2
    ├── currentLevel   → "component"
    ├── selectedId     → null
    ├── pendingNodeType→ null
    └── levels
        ├── "context"   (empty DiagramLevel)
        ├── "container" (empty DiagramLevel)
        ├── "component" (one node per module)
        └── "code"      (one node per class with parentNodeId; all resolved edges)
"""

from __future__ import annotations

from layup_parser._schema_path import SCHEMA_VERSION
from layup_parser.layout.hierarchical import (
    Position,
    layout_classes,
    layout_modules,
)
from layup_parser.models import (
    InheritanceEdge,
    MemberKind,
    MemberVisibility,
    NodeType,
    ParsedClass,
    ParsedMember,
    ParsedModule,
    ParsedPackage,
)

# ---------------------------------------------------------------------------
# Constants / mappings
# ---------------------------------------------------------------------------

# Map our NodeType enum to Layup's C4NodeType strings
_NODE_TYPE_MAP: dict[NodeType, str] = {
    NodeType.CLASS: "class",
    NodeType.ABSTRACT_CLASS: "abstract-class",
    NodeType.INTERFACE: "interface",
    NodeType.ENUM: "enum",
    NodeType.RECORD: "record",
}

# UML inheritance arrow: open hollow triangle at the parent end
_INHERITANCE_MARKER_END = "hollow-triangle"
_INHERITANCE_LINE_STYLE = "solid"


# ---------------------------------------------------------------------------
# Member serialisation
# ---------------------------------------------------------------------------


def _serialise_member(member: ParsedMember) -> dict:
    result: dict = {
        "id": member.id,
        "kind": member.kind.value,
        "visibility": member.visibility.value,
        "name": member.name,
    }
    if member.type_ is not None:
        result["type"] = member.type_
    if member.params is not None:
        result["params"] = member.params
    if member.is_static:
        result["isStatic"] = True
    if member.is_abstract:
        result["isAbstract"] = True
    return result


# ---------------------------------------------------------------------------
# Node serialisation
# ---------------------------------------------------------------------------


def _serialise_class_node(
    cls: ParsedClass,
    position: Position,
    parent_node_id: str | None = None,
) -> dict:
    """Emit a UML class node for the code level."""
    node: dict = {
        "id": cls.id,
        "type": _NODE_TYPE_MAP[cls.node_type],
        "label": cls.name,
        "position": position.to_dict(),
    }
    if cls.members:
        node["members"] = [_serialise_member(m) for m in cls.members]
    if parent_node_id is not None:
        node["parentNodeId"] = parent_node_id
    return node


def _serialise_module_node(mod: ParsedModule, position: Position) -> dict:
    """Emit a 'component' node on the component level representing one module."""
    return {
        "id": mod.id,
        "type": "component",
        "label": mod.name,
        "description": mod.file_path,
        "position": position.to_dict(),
    }


# ---------------------------------------------------------------------------
# Edge serialisation
# ---------------------------------------------------------------------------


def _serialise_inheritance_edge(edge: InheritanceEdge) -> dict:
    return {
        "id": edge.id,
        "source": edge.source_id,
        "target": edge.target_id,
        "markerEnd": _INHERITANCE_MARKER_END,
        "lineStyle": _INHERITANCE_LINE_STYLE,
    }


# ---------------------------------------------------------------------------
# Level builders
# ---------------------------------------------------------------------------


def _empty_level(level_key: str) -> dict:
    """Build an empty DiagramLevel dict for the given level key."""
    return {
        "level": level_key,
        "nodes": [],
        "edges": [],
        "annotations": [],
    }


def _build_component_level(
    package: ParsedPackage,
    module_positions: dict[str, Position],
) -> dict:
    """Build the component-level DiagramLevel (one node per module)."""
    nodes = [
        _serialise_module_node(mod, module_positions[mod.id])
        for mod in package.modules
        if mod.id in module_positions
    ]
    return {
        "level": "component",
        "nodes": nodes,
        "edges": [],
        "annotations": [],
    }


def _build_code_level(
    package: ParsedPackage,
    edges_by_mod: dict[str, list[InheritanceEdge]],
    class_positions_by_mod: dict[str, dict[str, Position]],
) -> dict:
    """Build a unified code-level DiagramLevel across all modules.

    Each class node carries ``parentNodeId`` set to its owning module's id.
    All resolved inheritance edges (including cross-module) are included.
    """
    all_nodes: list[dict] = []
    all_edges: list[dict] = []

    for mod in package.modules:
        class_positions = class_positions_by_mod.get(mod.id, {})
        for cls in mod.classes:
            if cls.id in class_positions:
                all_nodes.append(
                    _serialise_class_node(
                        cls,
                        class_positions[cls.id],
                        parent_node_id=mod.id,
                    )
                )
        for edge in edges_by_mod.get(mod.id, []):
            all_edges.append(_serialise_inheritance_edge(edge))

    return {
        "level": "code",
        "nodes": all_nodes,
        "edges": all_edges,
        "annotations": [],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_diagram_state(
    package: ParsedPackage,
    edges: list[InheritanceEdge],
    *,
    root_label: str | None = None,
) -> dict:
    """Build a Layup-compatible ``DiagramState`` dict (v2 schema).

    Parameters
    ----------
    package:
        A fully-populated :class:`~layup_parser.models.ParsedPackage`.
    edges:
        Resolved :class:`~layup_parser.models.InheritanceEdge` list from the
        relationship resolver.  All edges are rendered regardless of
        ``cross_module`` flag.
    root_label:
        Unused in v2 (DiagramLevel no longer has a label field). Kept for
        backwards-compatible call sites; the argument is silently ignored.

    Returns
    -------
    dict
        A Python dict representing a valid ``DiagramState`` JSON object.
    """
    # --- Layout ---
    module_positions = layout_modules(package.modules)

    # Group edges by source module (used for layout and serialisation)
    edges_by_mod: dict[str, list[InheritanceEdge]] = {
        mod.id: [] for mod in package.modules
    }
    for edge in edges:
        for mod in package.modules:
            if any(cls.id == edge.source_id for cls in mod.classes):
                edges_by_mod[mod.id].append(edge)
                break

    # Layout classes per module using same-module edges only (cross-module
    # edges still render correctly since both endpoint nodes exist in the
    # unified code level)
    class_positions_by_mod: dict[str, dict[str, Position]] = {}
    for mod in package.modules:
        same_mod_edges = [e for e in edges_by_mod.get(mod.id, []) if not e.cross_module]
        class_positions_by_mod[mod.id] = layout_classes(mod.classes, same_mod_edges)

    # --- Assemble levels ---
    levels = {
        "context": _empty_level("context"),
        "container": _empty_level("container"),
        "component": _build_component_level(package, module_positions),
        "code": _build_code_level(package, edges_by_mod, class_positions_by_mod),
    }

    return {
        "version": SCHEMA_VERSION,
        "currentLevel": "component",
        "selectedId": None,
        "pendingNodeType": None,
        "levels": levels,
    }
