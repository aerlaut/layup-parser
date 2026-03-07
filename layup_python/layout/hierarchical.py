"""Hierarchical layout engine.

Produces ``{x, y}`` positions for two diagram levels:

**Component-level** (root diagram — one node per module)
    Modules are arranged in a grid of at most ``MAX_COLUMNS`` columns,
    sorted alphabetically by module name.

**Code-level** (per-module diagram — one node per class)
    Classes are arranged using a layer-based topological layout:
    - Base classes appear at the top (layer 0).
    - Derived classes appear below their parents.
    - Isolated classes (no edges) occupy a final row.
    Within each layer nodes are distributed evenly horizontally.

All positions are pixel values suitable for direct use as Layup ``position``
objects.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from layup_python.models import InheritanceEdge, ParsedClass, ParsedModule

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Component-level (module nodes on root diagram)
MODULE_NODE_W = 240
MODULE_NODE_H = 80
MODULE_GAP_X = 80
MODULE_GAP_Y = 80
MAX_COLUMNS = 4

# Code-level (class nodes on per-module diagrams)
CLASS_NODE_W = 220
CLASS_BASE_H = 80
CLASS_MEMBER_H = 22   # additional height per class member
CLASS_GAP_X = 100
CLASS_GAP_Y = 160

# Canvas padding (top-left origin offset)
PADDING_X = 60
PADDING_Y = 60


# ---------------------------------------------------------------------------
# Public data structure
# ---------------------------------------------------------------------------


@dataclass
class Position:
    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y}


# ---------------------------------------------------------------------------
# Component-level layout
# ---------------------------------------------------------------------------


def layout_modules(modules: list[ParsedModule]) -> dict[str, Position]:
    """Assign grid positions to module nodes for the root component diagram.

    Parameters
    ----------
    modules:
        Ordered list of modules to lay out (typically alphabetical).

    Returns
    -------
    Mapping of ``module.id`` → :class:`Position`.
    """
    positions: dict[str, Position] = {}
    sorted_mods = sorted(modules, key=lambda m: m.name)
    col_stride = MODULE_NODE_W + MODULE_GAP_X
    row_stride = MODULE_NODE_H + MODULE_GAP_Y

    for idx, mod in enumerate(sorted_mods):
        col = idx % MAX_COLUMNS
        row = idx // MAX_COLUMNS
        positions[mod.id] = Position(
            x=PADDING_X + col * col_stride,
            y=PADDING_Y + row * row_stride,
        )

    return positions


# ---------------------------------------------------------------------------
# Code-level layout (layered / topological)
# ---------------------------------------------------------------------------


def _estimated_height(cls: ParsedClass) -> float:
    return CLASS_BASE_H + len(cls.members) * CLASS_MEMBER_H


def _build_layer_graph(
    classes: list[ParsedClass],
    edges: list[InheritanceEdge],
) -> dict[str, int]:
    """Assign a layer index to each class using Kahn's topological sort.

    Edges are directed *child → parent* (source = child, target = parent).
    We want parents at smaller layer numbers (closer to the top), so we
    invert the direction for layer assignment: treat *parent → child* as the
    DAG direction.

    Returns a mapping ``class_id → layer`` (0 = topmost / base classes).
    """
    class_ids = {c.id for c in classes}
    # Only consider same-module edges (cross-module edges are filtered earlier)
    relevant_edges = [
        e for e in edges
        if e.source_id in class_ids and e.target_id in class_ids
    ]

    # in-degree in the *parent → child* DAG
    # i.e. how many parents does each child have (within this module)
    in_degree: dict[str, int] = {c.id: 0 for c in classes}
    children_of: dict[str, list[str]] = defaultdict(list)  # parent → [children]

    for edge in relevant_edges:
        child_id = edge.source_id
        parent_id = edge.target_id
        in_degree[child_id] += 1
        children_of[parent_id].append(child_id)

    # Kahn's BFS: nodes with in_degree 0 are root/base classes (layer 0)
    layer: dict[str, int] = {}
    queue: deque[str] = deque()

    for cls_id, deg in in_degree.items():
        if deg == 0:
            queue.append(cls_id)
            layer[cls_id] = 0

    while queue:
        node = queue.popleft()
        for child in children_of[node]:
            in_degree[child] -= 1
            layer[child] = max(layer.get(child, 0), layer[node] + 1)
            if in_degree[child] == 0:
                queue.append(child)

    # Any class not yet assigned (e.g. isolated nodes or cycles) → last layer
    max_layer = max(layer.values(), default=0)
    for cls in classes:
        if cls.id not in layer:
            layer[cls.id] = max_layer + 1

    return layer


def layout_classes(
    classes: list[ParsedClass],
    edges: list[InheritanceEdge],
) -> dict[str, Position]:
    """Assign layered positions to class nodes for a code-level diagram.

    Parameters
    ----------
    classes:
        All classes belonging to the module being laid out.
    edges:
        All *same-module* inheritance edges (cross-module edges must be
        excluded by the caller).

    Returns
    -------
    Mapping of ``class.id`` → :class:`Position`.
    """
    if not classes:
        return {}

    layers = _build_layer_graph(classes, edges)

    # Group classes by layer, sorting within each layer by name for stability
    layer_to_classes: dict[int, list[ParsedClass]] = defaultdict(list)
    for cls in classes:
        layer_to_classes[layers[cls.id]].append(cls)
    for layer_classes in layer_to_classes.values():
        layer_classes.sort(key=lambda c: c.name)

    # Compute y-position for each layer
    # Each layer's y is the max bottom edge of all previous layers + gap
    sorted_layer_nums = sorted(layer_to_classes.keys())
    layer_y: dict[int, float] = {}
    current_y = float(PADDING_Y)

    for layer_num in sorted_layer_nums:
        layer_y[layer_num] = current_y
        max_h = max(_estimated_height(c) for c in layer_to_classes[layer_num])
        current_y += max_h + CLASS_GAP_Y

    # Compute x-positions: centre each layer's nodes horizontally
    # Use the widest layer as the reference width for centring
    max_layer_width = max(
        len(cs) * (CLASS_NODE_W + CLASS_GAP_X) - CLASS_GAP_X
        for cs in layer_to_classes.values()
    )

    positions: dict[str, Position] = {}

    for layer_num, layer_classes in layer_to_classes.items():
        n = len(layer_classes)
        layer_width = n * (CLASS_NODE_W + CLASS_GAP_X) - CLASS_GAP_X
        # Centre this layer relative to the widest layer
        x_offset = PADDING_X + (max_layer_width - layer_width) / 2
        y = layer_y[layer_num]

        for col, cls in enumerate(layer_classes):
            x = x_offset + col * (CLASS_NODE_W + CLASS_GAP_X)
            positions[cls.id] = Position(x=x, y=y)

    return positions
