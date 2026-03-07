"""Layup DiagramState JSON emitter.

Takes a fully-populated :class:`~layup_python.models.ParsedPackage` plus
resolved :class:`~layup_python.models.InheritanceEdge` objects and layout
positions, and returns a Python dict that validates against
``schema/diagram.schema.json``.

Output structure
----------------
::

    DiagramState
    ├── rootId        → "root"
    ├── diagrams
    │   ├── "root"   (component level — one node per module)
    │   └── "<mod_id>"  (code level — one node per class, edges for same-module inheritance)
    └── navigationStack → ["root"]

Cross-module inheritance edges are **not rendered** in v1 (they are returned
as warnings by the relationship resolver and should be surfaced to the user
via the CLI / API).
"""

from __future__ import annotations

from layup_python._schema_path import SCHEMA_VERSION
from layup_python.layout.hierarchical import (
    Position,
    layout_classes,
    layout_modules,
)
from layup_python.models import (
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

ROOT_DIAGRAM_ID = "root"

# Map our NodeType enum to Layup's C4NodeType strings
_NODE_TYPE_MAP: dict[NodeType, str] = {
    NodeType.CLASS: "class",
    NodeType.ABSTRACT_CLASS: "abstract-class",
    NodeType.INTERFACE: "interface",
    NodeType.ENUM: "enum",
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


def _serialise_class_node(cls: ParsedClass, position: Position, child_diagram_id: str | None = None) -> dict:
    node: dict = {
        "id": cls.id,
        "type": _NODE_TYPE_MAP[cls.node_type],
        "label": cls.name,
        "position": position.to_dict(),
    }
    if cls.members:
        node["members"] = [_serialise_member(m) for m in cls.members]
    if child_diagram_id is not None:
        node["childDiagramId"] = child_diagram_id
    return node


def _serialise_module_node(mod: ParsedModule, position: Position) -> dict:
    """Emit a 'component' node on the root diagram representing one module."""
    return {
        "id": mod.id,
        "type": "component",
        "label": mod.name,
        "description": mod.file_path,
        "position": position.to_dict(),
        "childDiagramId": mod.id,  # drills into the module's code diagram
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
# Diagram-level builders
# ---------------------------------------------------------------------------


def _build_root_diagram(
    package: ParsedPackage,
    root_label: str,
    module_positions: dict[str, Position],
) -> dict:
    """Build the component-level root DiagramLevel."""
    nodes = [
        _serialise_module_node(mod, module_positions[mod.id])
        for mod in package.modules
        if mod.id in module_positions
    ]
    return {
        "id": ROOT_DIAGRAM_ID,
        "level": "component",
        "label": root_label,
        "nodes": nodes,
        "edges": [],
        "annotations": [],
    }


def _build_module_diagram(
    mod: ParsedModule,
    same_module_edges: list[InheritanceEdge],
    class_positions: dict[str, Position],
) -> dict:
    """Build the code-level DiagramLevel for one module."""
    nodes = [
        _serialise_class_node(cls, class_positions[cls.id])
        for cls in mod.classes
        if cls.id in class_positions
    ]
    edges = [
        _serialise_inheritance_edge(e)
        for e in same_module_edges
    ]
    return {
        "id": mod.id,
        "level": "code",
        "label": mod.name,
        "nodes": nodes,
        "edges": edges,
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
    """Build a Layup-compatible ``DiagramState`` dict.

    Parameters
    ----------
    package:
        A fully-populated :class:`~layup_python.models.ParsedPackage`.
    edges:
        Resolved :class:`~layup_python.models.InheritanceEdge` list from the
        relationship resolver.  Cross-module edges are automatically excluded
        from rendering.
    root_label:
        Optional label for the root component diagram.  Defaults to the
        package name.

    Returns
    -------
    dict
        A Python dict representing a valid ``DiagramState`` JSON object.
    """
    label = root_label or package.name

    # --- Layout ---
    module_positions = layout_modules(package.modules)

    # Group edges by module: only same-module edges are rendered
    same_module_edges_by_mod: dict[str, list[InheritanceEdge]] = {
        mod.id: [] for mod in package.modules
    }
    for edge in edges:
        if not edge.cross_module:
            # Determine which module this edge belongs to (source's module)
            # Find source class
            for mod in package.modules:
                if any(cls.id == edge.source_id for cls in mod.classes):
                    same_module_edges_by_mod[mod.id].append(edge)
                    break

    # --- Diagrams map ---
    diagrams: dict[str, dict] = {}

    # Root diagram
    diagrams[ROOT_DIAGRAM_ID] = _build_root_diagram(package, label, module_positions)

    # Per-module code diagrams
    for mod in package.modules:
        mod_edges = same_module_edges_by_mod.get(mod.id, [])
        class_positions = layout_classes(mod.classes, mod_edges)
        diagrams[mod.id] = _build_module_diagram(mod, mod_edges, class_positions)

    return {
        "version": SCHEMA_VERSION,
        "rootId": ROOT_DIAGRAM_ID,
        "navigationStack": [ROOT_DIAGRAM_ID],
        "selectedId": None,
        "pendingNodeType": None,
        "diagrams": diagrams,
    }
